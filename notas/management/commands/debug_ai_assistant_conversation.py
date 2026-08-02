from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from notas.application.ai_intake.conversation_replay import (
    built_in_replay_scenarios,
    get_replay_scenario,
    run_replay_scenario,
)


class Command(BaseCommand):
    help = "Replay scripted AI Assistant conversations with fake provider responses."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scenario",
            default="dieta_con_ficha_tool_led",
            help="Built-in replay scenario key.",
        )
        parser.add_argument(
            "--list-scenarios",
            action="store_true",
            help="List available built-in replay scenarios.",
        )
        parser.add_argument("--show-tools", action="store_true", help="Print tool metadata per turn.")
        parser.add_argument("--show-state", action="store_true", help="Print NutritionBrief snapshot per turn.")
        parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
        parser.add_argument(
            "--no-assert-clean",
            action="store_true",
            help="Do not fail when replay cleanliness checks detect a regression.",
        )

    def handle(self, *args, **options):
        if options["list_scenarios"]:
            for key, scenario in built_in_replay_scenarios().items():
                self.stdout.write(f"{key}: {scenario.description}")
            return

        try:
            scenario = get_replay_scenario(options["scenario"])
            result = run_replay_scenario(scenario, assert_clean=not options["no_assert_clean"])
        except Exception as exc:  # pragma: no cover - command boundary
            raise CommandError(str(exc)) from exc

        if options["json"]:
            self.stdout.write(json.dumps(_result_as_dict(result), ensure_ascii=False, indent=2))
            return

        self.stdout.write(self.style.SUCCESS(f"Scenario OK: {scenario.key}"))
        self.stdout.write(f"Provider requests: {result.fake_provider_requests_count}")
        self.stdout.write("Invariants:")
        for outcome in result.invariant_outcomes():
            marker = "OK" if outcome.passed else "FAIL"
            self.stdout.write(f"  [{marker}] {outcome.key}: {outcome.detail}")
        for turn in result.turns:
            self.stdout.write("")
            self.stdout.write(f"[{turn.index}] USER: {turn.user_message}")
            self.stdout.write(f"[{turn.index}] ASSISTANT: {turn.visible_message}")
            if options["show_tools"]:
                self.stdout.write(f"[{turn.index}] TOOL META: {json.dumps(_tool_meta(turn.metadata), ensure_ascii=False)}")
            if options["show_state"]:
                self.stdout.write(f"[{turn.index}] BRIEF: {json.dumps(turn.brief_snapshot, ensure_ascii=False)}")
        self.stdout.write("")
        self.stdout.write("Final brief:")
        self.stdout.write(json.dumps(result.turns[-1].brief_snapshot, ensure_ascii=False, indent=2))


def _tool_meta(metadata: dict) -> dict:
    return {
        "tool_requests": metadata.get("llm_tool_requests") or metadata.get("tool_requests"),
        "tools_executed": metadata.get("llm_tools_executed") or metadata.get("tools_executed"),
        "tool_loop_iterations": metadata.get("tool_loop_iterations"),
        "tool_state_patches": metadata.get("llm_tool_state_patches_applied"),
        "profile_cards": metadata.get("llm_profile_draft_cards_rendered"),
        "preference_cards": metadata.get("llm_preference_draft_cards_rendered"),
        "proposal_cards": metadata.get("llm_proposal_preferences_cards_rendered"),
        "degraded": metadata.get("llm_degraded"),
        "degraded_reason": metadata.get("llm_degraded_reason"),
    }


def _result_as_dict(result) -> dict:
    return {
        "scenario": result.scenario.key,
        "description": result.scenario.description,
        "provider_requests": result.fake_provider_requests_count,
        "invariants": [
            {
                "key": outcome.key,
                "passed": outcome.passed,
                "detail": outcome.detail,
            }
            for outcome in result.invariant_outcomes()
        ],
        "turns": [
            {
                "index": turn.index,
                "user": turn.user_message,
                "assistant": turn.visible_message,
                "metadata": dict(turn.metadata),
                "brief": dict(turn.brief_snapshot),
                "tools": list(turn.tool_names),
                "cards": {
                    "profile": turn.profile_card_count,
                    "preference": turn.preference_card_count,
                    "proposal_preferences": turn.proposal_preferences_card_count,
                },
                "card_deltas": {
                    "profile": turn.profile_card_delta,
                    "preference": turn.preference_card_delta,
                    "proposal_preferences": turn.proposal_preferences_card_delta,
                },
            }
            for turn in result.turns
        ],
        "final_brief": dict(result.turns[-1].brief_snapshot) if result.turns else {},
    }

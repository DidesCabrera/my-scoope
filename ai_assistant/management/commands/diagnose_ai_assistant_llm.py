from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ai_assistant.application.provider_diagnostics import diagnose_llm_provider


class Command(BaseCommand):
    help = "Diagnose AI Assistant LLM provider configuration without changing chat behavior."

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider",
            dest="provider",
            default=None,
            help="Provider to diagnose. Defaults to AI_ASSISTANT_LLM_PROVIDER.",
        )
        parser.add_argument(
            "--live",
            action="store_true",
            help="Perform an explicit minimal live provider call. Disabled by default.",
        )
        parser.add_argument(
            "--fail-on-error",
            action="store_true",
            help="Exit with an error status when diagnostics are not ok.",
        )

    def handle(self, *args, **options):
        result = diagnose_llm_provider(
            provider_name=options.get("provider"),
            live=bool(options.get("live")),
        )

        self.stdout.write("AI Assistant LLM diagnostics")
        self.stdout.write("")
        self.stdout.write(f"provider: {result.provider}")
        self.stdout.write(f"configured: {str(result.configured).lower()}")
        self.stdout.write(f"client_buildable: {str(result.client_buildable).lower()}")
        if result.model:
            self.stdout.write(f"model: {result.model}")
        if result.base_url_configured is not None:
            self.stdout.write(f"base_url_configured: {str(result.base_url_configured).lower()}")
        if result.timeout_seconds is not None:
            self.stdout.write(f"timeout_seconds: {result.timeout_seconds}")
        self.stdout.write(f"live_check: {result.live_check}")
        if result.missing_settings:
            self.stdout.write("missing:")
            for setting_name in result.missing_settings:
                self.stdout.write(f"  - {setting_name}")
        if result.error_message:
            self.stdout.write(f"error: {result.error_message}")
        if result.live_response_provider:
            self.stdout.write(f"live_response_provider: {result.live_response_provider}")
        if result.live_response_model:
            self.stdout.write(f"live_response_model: {result.live_response_model}")
        if result.live_response_id:
            self.stdout.write(f"live_response_id: {result.live_response_id}")
        self.stdout.write(f"status: {result.status}")

        if options.get("fail_on_error") and not result.ok:
            raise CommandError(f"AI Assistant LLM diagnostics failed with status: {result.status}")

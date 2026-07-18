import json

from django.core.management.base import BaseCommand, CommandError

from core.product_portfolio import load_product_portfolio, validate_product_portfolio


class Command(BaseCommand):
    help = "Show My Scoope product bets, evidence, experiments, and reformulation signals."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args, **options):
        errors = validate_product_portfolio()
        if errors:
            raise CommandError("; ".join(errors))
        bets = load_product_portfolio()
        if options["as_json"]:
            self.stdout.write(json.dumps({
                "contract": "myscoope.product_portfolio.v1",
                "bets": [bet.as_dict() for bet in bets],
            }, ensure_ascii=False, indent=2, sort_keys=True))
            return
        self.stdout.write(f"My Scoope product portfolio: {len(bets)} bets")
        for bet in bets:
            self.stdout.write(f"[{bet.stage.upper()}] {bet.title}")
            self.stdout.write(f"  Next experiment: {bet.next_experiment}")


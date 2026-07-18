from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from core.product_portfolio import load_product_portfolio, validate_product_portfolio


class ProductPortfolioTests(SimpleTestCase):
    def test_portfolio_has_evidence_and_bidirectional_decision_signals(self):
        root = Path(settings.BASE_DIR)
        bets = load_product_portfolio(root)

        self.assertEqual(validate_product_portfolio(root), [])
        self.assertGreaterEqual(len(bets), 5)
        for bet in bets:
            self.assertTrue(bet.evidence)
            self.assertTrue(bet.continue_signals)
            self.assertTrue(bet.reformulate_signals)
            self.assertTrue(bet.next_experiment)

    def test_portfolio_is_not_a_fixed_deadline_roadmap(self):
        bets = load_product_portfolio(Path(settings.BASE_DIR))
        serialized = str([bet.as_dict() for bet in bets]).lower()

        self.assertNotIn("deadline", serialized)
        self.assertNotIn("target_date", serialized)

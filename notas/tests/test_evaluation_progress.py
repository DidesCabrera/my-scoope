import logging
from io import StringIO

from django.test import SimpleTestCase

from notas.application.ai_intake.evaluation_progress import evaluation_progress


class EvaluationProgressTests(SimpleTestCase):
    def test_safe_progress_is_flushed_and_logger_restored_on_failure(self):
        stream = StringIO()
        logger = logging.getLogger("myscoope.assistant.runtime")
        handlers, level = list(logger.handlers), logger.level
        with self.assertRaises(ValueError), evaluation_progress(True, stream):
            logger.info("culinary_week_start week=1")
            raise ValueError("sensitive details must not be logged")
        text = stream.getvalue()
        self.assertIn("lab_start", text)
        self.assertIn("week=1", text)
        self.assertIn("lab_failed type=ValueError", text)
        self.assertNotIn("sensitive", text)
        self.assertEqual(logger.handlers, handlers)
        self.assertEqual(logger.level, level)

    def test_disabled_progress_writes_nothing(self):
        stream = StringIO()
        with evaluation_progress(False, stream):
            pass
        self.assertEqual(stream.getvalue(), "")

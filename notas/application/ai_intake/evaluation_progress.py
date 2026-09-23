"""Opt-in stderr diagnostics: never log prompts, credentials or food/profile data."""

import faulthandler
import logging
from contextlib import contextmanager


@contextmanager
def evaluation_progress(enabled, stream):
    if not enabled:
        yield
        return
    logger = logging.getLogger("myscoope.assistant.runtime")
    previous_level = logger.level
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(asctime)s assistant_runtime %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    trace_enabled = False
    try:
        # StringIO in tests/embedded callers has no file descriptor.
        try:
            faulthandler.dump_traceback_later(60, repeat=True, file=stream)
            trace_enabled = True
        except (OSError, ValueError):
            pass
        logger.info("lab_start")
        yield
        logger.info("lab_done")
    except BaseException as exc:
        logger.error("lab_failed type=%s", type(exc).__name__)
        raise
    finally:
        if trace_enabled:
            faulthandler.cancel_dump_traceback_later()
        logger.removeHandler(handler)
        handler.close()
        logger.setLevel(previous_level)

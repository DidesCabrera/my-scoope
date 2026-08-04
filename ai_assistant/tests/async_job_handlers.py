def echo_job(*, job):
    return {"echo": job.request_payload.get("value"), "attempts": job.attempts}


def failing_job(*, job):
    raise RuntimeError(f"fixture failure {job.attempts}")

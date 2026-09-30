"""Typed weekly requirements shared by brief deserialization paths."""


def deserialize_program_fields(payload):
    duration = payload.get("duration_weeks")
    program_specification = payload.get("program_specification") or {}
    if program_specification:
        from nutrition_solver.application.program_specification import parse_program_specification
        program_specification = parse_program_specification(program_specification).as_dict()
        if duration is not None and duration != program_specification["duration_weeks"]:
            raise ValueError("program_spec_duration_conflict")
        duration = program_specification["duration_weeks"]
    if duration is not None and (type(duration) is not int or not 1 <= duration <= 8):
        raise ValueError("program_proposal_duration_must_be_1_to_8")
    return duration, program_specification

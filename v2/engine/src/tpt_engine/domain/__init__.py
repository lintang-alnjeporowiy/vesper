from .case import KEK, SCHEMA_VERSION, Case, teu_forms

__all__ = ["Case", "KEK", "SCHEMA_VERSION", "teu_forms", "load_case", "case_json_schema"]


def load_case(path) -> Case:
    """Baca & validasi file JSON kasus."""
    from pathlib import Path

    return Case.model_validate_json(Path(path).read_text(encoding="utf-8"))


def case_json_schema() -> dict:
    return Case.model_json_schema()

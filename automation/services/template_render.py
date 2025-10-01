from collections import UserDict
from typing import Dict, Any, Tuple


def normalize_key(k: str) -> str:
    return str(k).strip().lower()


class SafeDict(UserDict):
    def __missing__(self, key):
        return "{" + key + "}"


def build_context(row: Dict[str, Any]) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {}
    for k, v in row.items():
        ctx[str(k)] = "" if v is None else v
    for k, v in row.items():
        ctx[normalize_key(k)] = "" if v is None else v
    return ctx


def render_text(tpl: str, row: Dict[str, Any]) -> str:
    ctx = SafeDict(build_context(row))
    return (tpl or "").format_map(ctx)


def render_subject_body(subject_tpl: str, body_tpl: str, row: Dict[str, Any]) -> Tuple[str, str]:
    return render_text(subject_tpl, row), render_text(body_tpl, row)



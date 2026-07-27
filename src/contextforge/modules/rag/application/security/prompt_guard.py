from __future__ import annotations

import re

_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"system\s+prompt", re.I),
    re.compile(r"you\s+are\s+now", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"\[\s*system\s*\]", re.I),
    re.compile(r"override\s+safety", re.I),
)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_user_question(question: str, *, max_chars: int = 4000) -> str:
    cleaned = _CONTROL_CHARS.sub(" ", question or "").strip()
    cleaned = cleaned[:max_chars]
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[filtered]", cleaned)
    return cleaned


def wrap_untrusted_document(content: str, *, chunk_id: str) -> str:
    safe = _CONTROL_CHARS.sub(" ", content or "")
    for pattern in _INJECTION_PATTERNS:
        safe = pattern.sub("[filtered]", safe)
    return (
        f"UNTRUSTED_DOCUMENT_BEGIN cite={chunk_id}\n"
        f"{safe.strip()}\n"
        f"UNTRUSTED_DOCUMENT_END cite={chunk_id}"
    )


def build_context_block(chunks: list[tuple[str, str]]) -> str:
    parts = [wrap_untrusted_document(content, chunk_id=chunk_id) for chunk_id, content in chunks]
    return "\n\n".join(parts)


_UNTRUSTED_MARKERS = re.compile(
    r"UNTRUSTED_DOCUMENT_(?:BEGIN|END)(?:\s+cite=[^\s\n]+)?",
    re.IGNORECASE,
)


def wrap_conversation_history(history: str) -> str:
    safe = _CONTROL_CHARS.sub(" ", history or "").strip()
    for pattern in _INJECTION_PATTERNS:
        safe = pattern.sub("[filtered]", safe)
    if not safe:
        return ""
    return f"CONVERSATION_HISTORY_BEGIN\n{safe}\nCONVERSATION_HISTORY_END"


def sanitize_model_answer(answer: str) -> str:
    cleaned = _UNTRUSTED_MARKERS.sub(" ", answer or "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


__all__ = [
    "build_context_block",
    "sanitize_model_answer",
    "sanitize_user_question",
    "wrap_conversation_history",
    "wrap_untrusted_document",
]

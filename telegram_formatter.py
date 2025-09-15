"""Lightweight Telegram formatting helpers used in tests.

This is a simplified implementation created so the existing test suite
(`test_formatter.py`) and any higher–level pipelines can import a
`telegram_formatter` object plus the convenience function
`format_psychology_content`.

The goal is NOT to provide pixel‑perfect production formatting here –
only stable, dependency‑free helpers that exercise formatting logic and
won't break in constrained CI environments. If a richer implementation
is needed later it can replace these functions while keeping the same
public API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _to_persian_numbers(text: str) -> str:
    return (text or "").translate(PERSIAN_DIGITS)


@dataclass
class TelegramFormatter:
    header_prefix: str = "#"
    progress_bar_width: int = 20

    # --- Basic blocks -------------------------------------------------
    def format_header(self, text: str, level: int = 1) -> str:
        level = max(1, min(level, 6))
        return f"{self.header_prefix * level} {text.strip()}".rstrip()

    def format_numbered_list(self, items: Sequence[str]) -> str:
        lines = [f"{i+1}. {str(item).strip()}" for i, item in enumerate(items)]
        return "\n".join(lines) + ("\n" if lines else "")

    def format_list_item(self, text: str, style: str = "point") -> str:
        bullet = "•" if style == "point" else "-"
        return f"{bullet} {text.strip()}\n"

    # --- Domain specific ----------------------------------------------
    def format_personality_score(self, trait: str, score: int, desc: str) -> str:
        score = max(0, min(int(score), 100))
        bar = self.format_progress_bar(score, trait, compact=True)
        return f"{trait}: {score}%\n{bar}\n{desc.strip()}"

    def format_progress_bar(self, value: int, label: str = "", compact: bool = False) -> str:
        value = max(0, min(int(value), 100))
        filled = int(self.progress_bar_width * value / 100)
        bar = "█" * filled + "░" * (self.progress_bar_width - filled)
        if compact:
            return f"[{bar}] {value}%"
        return f"{label}: [{bar}] {value}%".strip()

    def format_highlight_box(self, text: str, title: str | None = None) -> str:
        lines = [l.rstrip() for l in (text or "").splitlines() if l.strip()]
        body = "\n".join(lines)
        if title:
            return f"*** {title} ***\n{body}\n***"  # simple delimiter style
        return f"***\n{body}\n***"

    # --- Tables -------------------------------------------------------
    def format_table(self, headers: Sequence[str], rows: Sequence[Sequence[str]], title: str | None = None) -> str:
        # Markdown table – minimal alignment logic
        headers = [str(h).strip() for h in headers]
        out = []
        if title:
            out.append(self.format_header(title, 3))
        out.append(" | ".join(headers))
        out.append(" | ".join(["---"] * len(headers)))
        for r in rows:
            out.append(" | ".join(str(c).strip() for c in r))
        return "\n".join(out)

    # --- Utilities ----------------------------------------------------
    def to_persian_numbers(self, text: str) -> str:
        return _to_persian_numbers(text)


telegram_formatter = TelegramFormatter()


def format_psychology_content(data: dict, content_type: str) -> List[str]:
    """Return a list of message chunks for the given psychology content.

    The production version might include intelligent chunk splitting; here we
    implement a simple one‑chunk strategy except for very large blocks where we
    split on double newlines to keep each chunk < ~2k chars.
    """
    ct = (content_type or "").lower()
    chunks: List[str] = []

    if ct == "analysis":
        analysis = data.get("analysis") or """نتیجه‌ای موجود نیست."""
        base = f"{telegram_formatter.format_header(data.get('test_name', 'نتیجه آزمون'), 2)}\n\n{analysis.strip()}"
        # naive splitting
        if len(base) <= 1800:
            chunks.append(base)
        else:
            for part in base.split("\n\n"):
                if part.strip():
                    chunks.append(part.strip())
        return chunks

    if ct == "question":
        q = data.get("question", "سوال")
        number = data.get("number", 1)
        total = data.get("total") or "?"
        opts = data.get("options", [])
        opts_text = telegram_formatter.format_numbered_list(opts)
        text = f"{telegram_formatter.to_persian_numbers(f'سوال {number} از {total}')}\n{q}\n\n{opts_text}".strip()
        return [text]

    if ct == "acknowledgment":
        ack = data.get("acknowledgment", "")
        user_resp = data.get("user_response", "")
        txt = f"✅ {ack}\n🗣️ {user_resp}".strip()
        return [txt]

    if ct == "error":
        err = data.get("error", "خطای نامشخص")
        sug = data.get("suggestion")
        txt = f"⚠️ {err}\n{('💡 ' + sug) if sug else ''}".strip()
        return [txt]

    # Fallback – serialize dict compactly
    chunks.append(str(data))
    return chunks


__all__ = [
    "telegram_formatter",
    "format_psychology_content",
    "TelegramFormatter",
]

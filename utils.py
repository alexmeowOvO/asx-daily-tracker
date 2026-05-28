"""Shared utility functions for the Evening Wrap pipeline."""

import re


def _fix_mojibake(text: str) -> str:
    """Repair common UTF-8-as-cp1252 mojibake sequences."""
    if not text:
        return text
    suspects = ("\xe2\x80\x99", "\xe2\x80\x9c", "\xe2\x80", "\xc2", "\xc3", "\xf0\x9f")
    if not any(s in text for s in suspects):
        return text
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _clean_article_content(content: str) -> str:
    """Clean article content — strip metadata, author bio; keep [IMAGE:N] markers."""
    if not content:
        return content

    image_pattern = r"\[IMAGE:\d+\]"

    more_match = re.search(r"\+\d+ more\n+", content)
    if more_match:
        content = content[more_match.end():]

    for pat in [r"The S&P/ASX \d+", r"The ASX \d+", r"Australian shares"]:
        match = re.search(pat, content, re.IGNORECASE)
        if match:
            before = content[:match.start()]
            markers_before = re.findall(image_pattern, before)
            content = content[match.start():]
            if markers_before:
                content = "\n\n".join(markers_before) + "\n\n" + content
            break

    author_match = re.search(r"\nABOUT THE AUTHOR\n", content, re.IGNORECASE)
    if author_match:
        content = content[:author_match.start()]

    return content.strip()

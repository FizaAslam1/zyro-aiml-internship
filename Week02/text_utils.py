"""
Week 3 addition: text cleaning / normalization utilities.

Shared between train_classifier.py and app.py so that the SAME cleaning
is applied at training time and at inference time (this matters a lot for
TF-IDF based models - mismatched preprocessing silently hurts accuracy).
"""

import re


def clean_text(text: str) -> str:
    """
    Basic but effective cleanup for OCR / PDF extracted text:
    - collapse repeated whitespace and blank lines
    - strip weird control characters
    - normalize common OCR confusions is NOT done here (kept in extraction
      layer instead, since over-aggressive replacement can break regex on
      real words) - we only do safe, generic cleanup here.
    """
    if not text:
        return ""

    # remove non-printable / control characters (keep newlines)
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", text)

    # collapse multiple spaces/tabs into one
    text = re.sub(r"[ \t]+", " ", text)

    # collapse 3+ newlines into a max of 2 (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # strip trailing spaces on each line
    text = "\n".join(line.strip() for line in text.split("\n"))

    # remove fully empty leading/trailing lines
    text = text.strip()

    return text


def is_text_too_short(text: str, min_chars: int = 20) -> bool:
    """Used to decide whether extracted text is usable or we should fall back."""
    return len(text.strip()) < min_chars

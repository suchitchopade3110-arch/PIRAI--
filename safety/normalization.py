import base64
import re
import unicodedata
from typing import List

MAX_INSPECTION_CHARS = 12000
MAX_ENCODED_CHARS = 4096
ZERO_WIDTH = re.compile("[\u200b-\u200f\u2060\ufeff]")
BASE64_TOKEN = re.compile(r"(?<![A-Za-z0-9+/=])([A-Za-z0-9+/]{24,}={0,2})(?![A-Za-z0-9+/=])")
LEET_TABLE = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text or "")[:MAX_INSPECTION_CHARS])
    value = ZERO_WIDTH.sub("", value).lower().translate(LEET_TABLE)
    value = re.sub(r"(?<=\w)[\s._\-*/\\|,:;!?]+(?=\w)", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"(?<!\w)(?:[a-z0-9]\s+){3,}[a-z0-9](?!\w)", lambda match: match.group(0).replace(" ", ""), value)
    return value


def compact_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_text(text))


def inspection_variants(text: str) -> List[str]:
    raw = str(text or "")[:MAX_INSPECTION_CHARS]
    variants = [normalize_text(raw)]
    compact = compact_text(raw)
    if compact:
        variants.append(compact)

    stripped = raw.strip()
    if 12 <= len(stripped) <= 512:
        reversed_text = normalize_text(stripped[::-1])
        if reversed_text != variants[0]:
            variants.append(reversed_text)

    for match in BASE64_TOKEN.finditer(raw[:MAX_ENCODED_CHARS]):
        token = match.group(1)
        try:
            padding = "=" * (-len(token) % 4)
            decoded = base64.b64decode(token + padding, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        if decoded.isprintable():
            variants.append(normalize_text(decoded[:1024]))
    return list(dict.fromkeys(variants))

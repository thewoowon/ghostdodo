"""Korean company name normalization and alias generation.

Directory imports are messy in predictable ways: the same employer appears as
`주식회사 카카오`, `(주)카카오`, `카카오(주)`, and `카카오` across sources and
across years. Matching on the raw string would create four companies, split
the observations between them, and keep every one of them under the
publishable sample bar forever.

So normalization is not cosmetic here — it is what makes the metrics work.
"""

from __future__ import annotations

import re
import unicodedata

# Legal-form markers, stripped for matching but preserved in the legal name.
_LEGAL_FORMS_KO = (
    "주식회사",
    "유한회사",
    "유한책임회사",
    "합자회사",
    "합명회사",
    "사단법인",
    "재단법인",
    "의료법인",
    "학교법인",
    "협동조합",
    "농업회사법인",
)
_LEGAL_FORMS_EN = ("Inc", "Corp", "Corporation", "Ltd", "Limited", "Co", "LLC", "PLC", "GmbH")

_PAREN_FORMS = re.compile(r"\(\s*(주|유|재|사|합|학)\s*\)")
_LEGAL_KO_RE = re.compile("|".join(_LEGAL_FORMS_KO))
_LEGAL_EN_RE = re.compile(r"\b(" + "|".join(_LEGAL_FORMS_EN) + r")\b\.?", re.IGNORECASE)
_NON_NAME = re.compile(r"[^\w가-힣]+", re.UNICODE)
_WS = re.compile(r"\s+")


def strip_legal_form(name: str) -> str:
    """Removes legal-entity markers. `(주)도도랩` and `주식회사 도도랩` both
    become `도도랩`."""
    without = _PAREN_FORMS.sub(" ", name)
    without = _LEGAL_KO_RE.sub(" ", without)
    without = _LEGAL_EN_RE.sub(" ", without)
    return _WS.sub(" ", without).strip()


def match_key(name: str) -> str:
    """The key two records must share to be considered the same company.

    Aggressive on purpose: case-folded, punctuation- and space-free, NFKC
    normalized so full-width and half-width characters collapse together.
    Used only for dedupe — never shown to a user.
    """
    base = unicodedata.normalize("NFKC", strip_legal_form(name)).casefold()
    return _NON_NAME.sub("", base)


def display_name(name: str) -> str:
    """The name shown in search results: legal form dropped, spacing tidied."""
    stripped = strip_legal_form(name)
    return stripped or _WS.sub(" ", name).strip()


def generate_aliases(*names: str | None) -> list[str]:
    """Every spelling a user might plausibly type for this company.

    Includes the raw legal names, the stripped forms, and the common
    parenthetical variants, so search matches whichever form the user knows.
    """
    aliases: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        cleaned = _WS.sub(" ", value).strip()
        if not cleaned or len(cleaned) > 200:
            return
        key = cleaned.casefold()
        if key in seen:
            return
        seen.add(key)
        aliases.append(cleaned)

    for name in names:
        if not name:
            continue
        add(name)
        stripped = strip_legal_form(name)
        add(stripped)
        if stripped and stripped != name:
            # The two orderings Korean companies actually use.
            add(f"(주){stripped}")
            add(f"주식회사 {stripped}")

    return aliases


_SLUG_SAFE = re.compile(r"[^a-z0-9가-힣]+")


def slugify(name: str, *, fallback: str) -> str:
    """URL slug. Korean is kept — it is readable and legal in a URL path —
    with a stable fallback when a name has no usable characters."""
    base = unicodedata.normalize("NFKC", strip_legal_form(name)).casefold()
    slug = _SLUG_SAFE.sub("-", base).strip("-")
    return slug[:100] or fallback

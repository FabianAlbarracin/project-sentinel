import re

DEAL_THRESHOLD = 2

PRICE_RE = re.compile(r"\$\d+(?:,\d{3})*(?:\.\d{2})?")

DISCOUNT_RE = re.compile(r"\b(\d+)\s*%\s*off\b", re.IGNORECASE)

SAVE_AMOUNT_RE = re.compile(
    r"\b(save|saving)\s+(\$?\d+(?:,\d{3})*(?:\.\d{2})?|up\s+to|money|big|huge|now|today|you)\b",
    re.IGNORECASE,
)

POSITIVE_SIGNALS = [
    (re.compile(r"\b(sale|discounts?|clearance|refurbished|renewed)\b", re.IGNORECASE), 2),
    (re.compile(r"\b(price\s+drop|marked\s+down|price\s+cut)\b", re.IGNORECASE), 2),
    (re.compile(r"\b(coupon|coupon\s+code|promo\s+code|use\s+code|with\s+code)\b", re.IGNORECASE), 2),
    (re.compile(r"\b(prime\s+day|black\s+friday|cyber\s+monday)\b", re.IGNORECASE), 2),
    (re.compile(r"\b(amazon|woot|target|best\s+buy|walmart|ebay)\b", re.IGNORECASE), 1),
]

NEGATIVE_SIGNALS = [
    (re.compile(
        r"\b(can\s+i|how\s+to|how\s+do|should\s+i|does\s+anyone|is\s+it\s+worth|"
        r"anyone\s+else|what\s+is|what\s+are|where\s+can|which\s+one|is\s+there"
        r"|has\s+anyone|would\s+you|any\s+recommendations?)\b",
        re.IGNORECASE,
    ), -3),
    (re.compile(
        r"\b(factory\s+reset|not\s+working|won'?t\s+turn\s+on|battery\s+drain|"
        r"stuck|frozen|bricked|repair|broken|replacement|defective|glitch|"
        r"troubleshoot)\b",
        re.IGNORECASE,
    ), -3),
    (re.compile(r"\b(issues?|problems?|errors?|bugs?|crash(?:es)?)\b", re.IGNORECASE), -2),
    (re.compile(r"\b(my\s+review|thoughts\s+on|just\s+got|finally\s+got)\b", re.IGNORECASE), -2),
    (re.compile(
        r"\b(kindle\s+edition|kindle\s+ebook|free\s+ebook|free\s+book|ebook"
        r"|pdf\s+digest|software|app)\b",
        re.IGNORECASE,
    ), -2),
    (re.compile(r"\b(save|saving)\s+.*?\b(highlights?|notes?|battery|files?|annotations?|bookmarks?|data)\b", re.IGNORECASE), -2),
]


def score_text(text: str) -> int:
    lower = text.lower()
    score = 0

    if PRICE_RE.search(text):
        score += 3

    if DISCOUNT_RE.search(lower):
        score += 3

    if SAVE_AMOUNT_RE.search(lower):
        score += 2

    for pattern, weight in POSITIVE_SIGNALS:
        if pattern.search(lower):
            score += weight

    for pattern, weight in NEGATIVE_SIGNALS:
        if pattern.search(lower):
            score += weight

    return score


def is_deal(text: str) -> bool:
    return score_text(text) >= DEAL_THRESHOLD

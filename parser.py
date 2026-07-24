"""
Разбор свободного текста вида "кофе 1000", "1000 кофе", "такси 2500 тг"
на сумму, описание и тип операции (расход/доход).
"""

import re

# Число: целое или с точкой/запятой (1000, 1500.50, 1 500, 1500,50)
AMOUNT_RE = re.compile(r"(\d[\d\s]*[.,]?\d*)")
INCOME_KEYWORDS = ("доход", "зарплата", "зп", "salary", "премия", "income", "поступление")
SEPARATORS_RE = re.compile(r"\s*(?:,|;|\n|\s+и\s+)\s*")


def parse_transaction(text: str) -> tuple[float, str, str] | None:
    """Возвращает (сумма, описание, тип) или None, если сумму найти не удалось."""
    text = text.strip()
    if not text:
        return None

    sign = None
    if text.startswith("+"):
        sign = "income"
        text = text[1:].strip()
    elif text.startswith("-"):
        sign = "expense"
        text = text[1:].strip()

    match = AMOUNT_RE.search(text)
    if not match:
        return None

    raw_amount = match.group(1)
    cleaned = raw_amount.replace(" ", "").replace(",", ".")
    try:
        amount = float(cleaned)
    except ValueError:
        return None

    if amount <= 0:
        return None

    description = text[: match.start()] + text[match.end():]
    description = re.sub(r"\b(тг|тенге|kzt|₸|руб|рублей|р\.)\b", "", description, flags=re.IGNORECASE)
    description = re.sub(r"^(доход|расход|expense|income|трата|потрата)\s*", "", description, flags=re.IGNORECASE)
    description = description.strip(" -,.")

    if not description:
        description = "без описания"

    lowered = description.lower()
    transaction_type = "income" if sign == "income" or any(keyword in lowered for keyword in INCOME_KEYWORDS) else "expense"
    return amount, description, transaction_type


def parse_transactions(text: str) -> list[tuple[float, str, str]]:
    """Разбирает одно сообщение на несколько операций, если там есть несколько частей."""
    text = text.strip()
    if not text:
        return []

    parts = [part.strip() for part in SEPARATORS_RE.split(text) if part.strip()]
    if not parts:
        return []

    if len(parts) == 1:
        parsed = parse_transaction(parts[0])
        return [parsed] if parsed is not None else []

    parsed_parts = []
    for part in parts:
        parsed = parse_transaction(part)
        if parsed is not None:
            parsed_parts.append(parsed)
    return parsed_parts


def parse_expense(text: str) -> tuple[float, str] | None:
    parsed = parse_transaction(text)
    if parsed is None:
        return None
    amount, description, _transaction_type = parsed
    return amount, description

"""
Формирование отчёта за месяц: текстовая сводка по категориям + столбчатая диаграмма.
"""

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import Workbook

from database import get_category_totals, get_month_transactions

MONTH_NAMES_RU = [
    "", "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]


async def build_text_report(user_id: int, year: int, month: int) -> str:
    totals = await get_category_totals(user_id, year, month)
    rows = await get_month_transactions(user_id, year, month)

    if not rows:
        return f"За {MONTH_NAMES_RU[month]} {year} записей пока нет."

    income_total = sum(row[1] for row in rows if row[4] == "income")
    expense_total = sum(row[1] for row in rows if row[4] == "expense")
    balance = income_total - expense_total
    total_sum = sum(totals.values())
    lines = [f"📊 Отчёт за {MONTH_NAMES_RU[month]} {year}", ""]
    lines.append(f"Доходы: {income_total:,.0f} тг".replace(",", " "))
    lines.append(f"Расходы: {expense_total:,.0f} тг".replace(",", " "))
    lines.append(f"Баланс: {balance:+,.0f} тг".replace(",", " "))

    if totals:
        lines.append("")
        lines.append("По категориям расходов:")
        for category, amount in sorted(totals.items(), key=lambda x: -x[1]):
            share = amount / total_sum * 100 if total_sum else 0
            lines.append(f"• {category}: {amount:,.0f} тг ({share:.0f}%)".replace(",", " "))

    lines.append("")
    lines.append(f"Количество записей: {len(rows)}")
    return "\n".join(lines)


async def build_chart(user_id: int, year: int, month: int) -> io.BytesIO | None:
    totals = await get_category_totals(user_id, year, month)
    if not totals:
        return None

    categories = list(totals.keys())
    amounts = list(totals.values())

    sorted_pairs = sorted(zip(categories, amounts), key=lambda x: -x[1])
    categories, amounts = zip(*sorted_pairs)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.barh(categories, amounts, color="#4C6EF5")
    ax.invert_yaxis()
    ax.set_xlabel("Тенге")
    ax.set_title(f"Траты по категориям — {MONTH_NAMES_RU[month]} {year}")

    for bar, amount in zip(bars, amounts):
        ax.text(
            bar.get_width(), bar.get_y() + bar.get_height() / 2,
            f" {amount:,.0f}".replace(",", " "),
            va="center", fontsize=9,
        )

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


async def export_month_excel(user_id: int, year: int, month: int) -> io.BytesIO:
    rows = await get_month_transactions(user_id, year, month)
    wb = Workbook()
    sheet = wb.active
    sheet.title = "transactions"
    sheet.append(["id", "amount", "category", "description", "transaction_type", "created_at"])

    for row in rows:
        sheet.append(list(row))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

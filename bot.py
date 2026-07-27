"""
Telegram-бот учёта финансов.

Запуск:
    python bot.py
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime, date

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from config import BOT_TOKEN
from database import (
    init_db,
    add_transaction,
    delete_last_expense,
    delete_all_user_data,
    update_entry_category,
    set_category_limit,
    remove_category_limit,
    get_category_limit,
    get_category_month_total,
    list_category_limits,
    get_history,
    add_recurring_rule,
    list_recurring_rules,
    get_due_recurring_rules,
    advance_recurring_rule,
    update_recurring_rule,
    delete_recurring_rule,
    get_recurring_rule_by_id,
    get_month_recurring_rules,
)
from categorizer import detect_category, all_categories, normalize_category
from parser import parse_transaction, parse_transactions
from voice import transcribe_voice
from report import build_text_report, build_chart, export_month_excel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

HELP_TEXT = (
    "👋 Я помогу вести учёт финансов.\n\n"
    "Просто напиши запись в свободной форме:\n"
    "  <i>кофе 1000</i>\n"
    "  <i>+150000 зарплата</i>\n"
    "  <i>обед в кафе 3200 тг</i>\n\n"
    "Также можно отправить голосовое сообщение — я его распознаю.\n\n"
    "Команды:\n"
    "/report — отчёт за текущий месяц\n"
    "/report 2026-06 — отчёт за конкретный месяц\n"
    "/export — Excel за текущий месяц\n"
    "/categories — список категорий\n"
    "/undo — удалить последнюю запись\n"
    "/setlimit \"Транспорт\" 15000 — задать лимит категории\n"
    "/limits — показать активные лимиты и текущий прогресс\n"
    "/removelimit \"Транспорт\" — удалить лимит категории\n"
    "/history — история за текущий месяц\n"
    "/history 2026-07 — история за конкретный месяц\n"
    "/recurring add 5000 аренда Дом и коммуналка — добавить повторяющуюся запись\n"
    "/recurring list — список повторяющихся записей\n"
    "/recurring edit <id> <сумма> [категория] — редактировать повторяющуюся запись\n"
    "/recurring remove <id> — удалить повторяющуюся запись\n"
    "/clearall — удалить все записи, лимиты и повторяющиеся правила\n"
)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(HELP_TEXT)


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@dp.message(Command("categories"))
async def cmd_categories(message: Message) -> None:
    cats = "\n".join(f"• {c}" for c in all_categories())
    await message.answer(f"Категории:\n{cats}")


@dp.message(Command("undo"))
async def cmd_undo(message: Message) -> None:
    deleted = await delete_last_expense(message.from_user.id)
    if deleted is None:
        await message.answer("Записей пока нет — нечего удалять.")
        return
    amount, category, description = deleted
    await message.answer(f"Удалено: {amount:,.0f} тг — {category} ({description})".replace(",", " "))


@dp.message(Command("report"))
async def cmd_report(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    now = datetime.now()
    year, month = now.year, now.month

    if len(parts) == 2:
        try:
            year_str, month_str = parts[1].strip().split("-")
            year, month = int(year_str), int(month_str)
        except ValueError:
            await message.answer("Формат: /report 2026-06 (год-месяц)")
            return

    text = await build_text_report(message.from_user.id, year, month)
    chart = await build_chart(message.from_user.id, year, month)

    if chart:
        photo = BufferedInputFile(chart.read(), filename="report.png")
        await message.answer_photo(photo, caption=text)
    else:
        await message.answer(text)


@dp.message(Command("export"))
async def cmd_export(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    now = datetime.now()
    year, month = now.year, now.month

    if len(parts) == 2:
        try:
            year_str, month_str = parts[1].strip().split("-")
            year, month = int(year_str), int(month_str)
        except ValueError:
            await message.answer("Формат: /export 2026-06 (год-месяц)")
            return

    workbook = await export_month_excel(message.from_user.id, year, month)
    filename = f"finance_{year}-{month:02d}.xlsx"
    await message.answer_document(
        BufferedInputFile(workbook.read(), filename=filename),
        caption=f"Экспорт за {year}-{month:02d}",
    )


@dp.message(Command("setlimit"))
async def cmd_setlimit(message: Message) -> None:
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Формат: /setlimit \"Транспорт\" 15000")
        return

    category_input = parts[1].strip().strip('"')
    category = normalize_category(category_input)
    
    if category is None:
        cats = ", ".join(all_categories()[:5])
        await message.answer(
            f"❌ Категория '{category_input}' не найдена.\n\n"
            f"Доступные категории: {cats} и другие.\n"
            f"Используйте /categories для полного списка."
        )
        return
    
    try:
        amount = float(parts[2])
    except ValueError:
        await message.answer("Формат: /setlimit \"Транспорт\" 15000")
        return

    await set_category_limit(message.from_user.id, category, amount)
    await message.answer(f"Лимит для категории {category}: {amount:,.0f} тг/мес установлен.".replace(",", " "))


@dp.message(Command("limits"))
async def cmd_limits(message: Message) -> None:
    now = datetime.now()
    limits = await list_category_limits(message.from_user.id, now.year, now.month)
    if not limits:
        await message.answer("Пока нет активных лимитов по категориям.")
        return

    lines = ["📌 Активные лимиты:"]
    for category, limit_amount, current, remaining in limits:
        if current >= limit_amount:
            status = "🚨 превышен"
        elif current >= limit_amount * 0.8:
            status = "⚠️ близко к лимиту"
        else:
            status = "✅ в норме"
        lines.append(
            f"• {category}: лимит {limit_amount:,.0f} тг, потрачено {current:,.0f} тг, осталось {remaining:,.0f} тг — {status}".replace(",", " ")
        )
    await message.answer("\n".join(lines))


@dp.message(Command("removelimit"))
async def cmd_removelimit(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Формат: /removelimit \"Транспорт\"")
        return

    category_input = parts[1].strip().strip('"')
    category = normalize_category(category_input)
    
    if category is None:
        await message.answer(f"❌ Категория '{category_input}' не найдена.")
        return
    
    removed = await remove_category_limit(message.from_user.id, category)
    if removed:
        await message.answer(f"Лимит для категории {category} удалён.")
    else:
        await message.answer(f"Лимит для категории {category} не найден.")


@dp.message(Command("clearall"))
async def cmd_clearall(message: Message) -> None:
    deleted_count = await delete_all_user_data(message.from_user.id)
    if deleted_count:
        await message.answer("🧹 Все ваши записи, лимиты и повторяющиеся правила удалены.")
    else:
        await message.answer("Пока нет данных для очистки.")


@dp.message(Command("history"))
async def cmd_history(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    now = datetime.now()
    year, month = now.year, now.month

    if len(parts) == 2:
        try:
            year_str, month_str = parts[1].strip().split("-")
            year, month = int(year_str), int(month_str)
        except ValueError:
            await message.answer("Формат: /history 2026-07 (год-месяц)")
            return

    rows = await get_history(message.from_user.id, year, month)
    if not rows:
        await message.answer(f"За {year}-{month:02d} записей нет.")
        return

    lines = [f"🗒 История за {year}-{month:02d}:"]
    for entry_id, amount, category, description, transaction_type, created_at in rows:
        created_dt = datetime.fromisoformat(created_at)
        time_str = created_dt.strftime("%d.%m.%Y %H:%M")
        sign = "+" if transaction_type == "income" else "-"
        lines.append(f"• {time_str} — {sign}{amount:,.0f} тг — {category} — {description}".replace(",", " "))
    await message.answer("\n".join(lines))


@dp.message(Command("recurring"))
async def cmd_recurring(message: Message) -> None:
    parts = message.text.split(maxsplit=4)
    
    # /recurring add 5000 аренда Дом и коммуналка
    if len(parts) >= 5 and parts[1] == "add":
        try:
            amount = float(parts[2])
            description = parts[3]
            category = " ".join(parts[4:])
        except ValueError:
            await message.answer("Формат: /recurring add 5000 аренда Дом и коммуналка")
            return
        rule_id = await add_recurring_rule(message.from_user.id, description, amount, category)
        await message.answer(f"Добавлено правило #{rule_id}: {description} — {amount:,.0f} тг в категории {category}".replace(",", " "))
        return
    
    # /recurring edit <id> <amount> [category]
    if len(parts) >= 3 and parts[1] == "edit":
        try:
            rule_id = int(parts[2])
            amount = float(parts[3]) if len(parts) > 3 else None
            category = " ".join(parts[4:]) if len(parts) > 4 else None
        except (ValueError, IndexError):
            await message.answer("Формат: /recurring edit <id> <сумма> [категория]")
            return
        
        rule = await get_recurring_rule_by_id(rule_id)
        if rule is None:
            await message.answer(f"Правило #{rule_id} не найдено.")
            return
        
        if amount is None:
            await message.answer("Нужно указать хотя бы сумму. Формат: /recurring edit <id> <сумма> [категория]")
            return
        
        updated = await update_recurring_rule(rule_id, amount, category)
        if updated:
            new_amount = amount or rule[2]
            new_category = category or rule[3]
            await message.answer(f"✅ Правило #{rule_id} обновлено: {new_amount:,.0f} тг в категории {new_category}".replace(",", " "))
        else:
            await message.answer(f"Не удалось обновить правило #{rule_id}.")
        return
    
    # /recurring remove <id>
    if len(parts) >= 3 and parts[1] == "remove":
        try:
            rule_id = int(parts[2])
        except ValueError:
            await message.answer("Формат: /recurring remove <id>")
            return
        
        rule = await get_recurring_rule_by_id(rule_id)
        if rule is None:
            await message.answer(f"Правило #{rule_id} не найдено.")
            return
        
        deleted = await delete_recurring_rule(rule_id)
        if deleted:
            await message.answer(f"✅ Правило #{rule_id} ({rule[1]} — {rule[2]:,.0f} тг) удалено.".replace(",", " "))
        else:
            await message.answer(f"Не удалось удалить правило #{rule_id}.")
        return
    
    # /recurring list (default)
    rules = await list_recurring_rules(message.from_user.id)
    if not rules:
        await message.answer("Пока нет повторяющихся правил.")
        return

    lines = ["Повторяющиеся записи:"]
    for rule_id, description, amount, category, interval, next_due_date in rules:
        lines.append(f"• #{rule_id} {description} — {amount:,.0f} тг, {category}, next: {next_due_date}".replace(",", " "))
    await message.answer("\n".join(lines))


async def _maybe_warn_limit(user_id: int, category: str, amount: float, year: int, month: int) -> None:
    limit = await get_category_limit(user_id, category)
    if limit is None or limit <= 0:
        return

    current_total = await get_category_month_total(user_id, category, year, month)
    new_total = current_total + amount

    if current_total < limit * 0.8 and new_total >= limit * 0.8:
        await bot.send_message(
            user_id,
            f"⚠️ Лимит по категории {category} достиг 80% ({new_total:,.0f} / {limit:,.0f} тг). Рекомендуем сократить расходы в этой категории.".replace(",", " "),
        )
    elif current_total < limit and new_total >= limit:
        await bot.send_message(
            user_id,
            f"🚨 Лимит по категории {category} уже исчерпан ({new_total:,.0f} / {limit:,.0f} тг). Лучше временно сократить траты в этой категории.".replace(",", " "),
        )
    elif new_total > limit:
        await bot.send_message(
            user_id,
            f"⚠️ Вы превысили лимит по категории {category} ({new_total:,.0f} / {limit:,.0f} тг). Рекомендуем перенести часть расходов на другой период или уменьшить траты.".replace(",", " "),
        )


async def _process_transaction(message: Message, text: str) -> None:
    parsed_items = parse_transactions(text)
    if not parsed_items:
        await message.answer(
            "Не нашёл сумму в сообщении 🤔\n"
            "Попробуй в формате: <i>кофе 1000</i>, <i>такси 2000, кофе 3000</i> или <i>+150000 зарплата</i>"
        )
        return

    now = datetime.now()
    saved_entries = []
    for amount, description, transaction_type in parsed_items:
        category = detect_category(description, transaction_type)
        entry_id = await add_transaction(message.from_user.id, amount, category, description, transaction_type)
        await _maybe_warn_limit(message.from_user.id, category, amount, now.year, now.month)

        sign = "+" if transaction_type == "income" else "-"
        saved_entries.append({
            "id": entry_id,
            "amount": amount,
            "description": description,
            "category": category,
            "sign": sign,
        })

    # Для одной записи показываем сразу кнопки с категориями
    if len(saved_entries) == 1:
        entry = saved_entries[0]
        text_msg = f"✅ {entry['sign']}{entry['amount']:,.0f} тг — {entry['description']}\nКатегория: {entry['category']}".replace(",", " ")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=cat, callback_data=f"category:{entry['id']}:{cat}") for cat in all_categories()[:4]],
                [InlineKeyboardButton(text=cat, callback_data=f"category:{entry['id']}:{cat}") for cat in all_categories()[4:8]],
                [InlineKeyboardButton(text=cat, callback_data=f"category:{entry['id']}:{cat}") for cat in all_categories()[8:]],
            ]
        )
        await message.answer(text_msg, reply_markup=keyboard)
    
    # Для нескольких записей показываем список с кнопками для каждой
    elif len(saved_entries) > 1:
        text_msgs = []
        for entry in saved_entries:
            text_msgs.append(f"✅ {entry['sign']}{entry['amount']:,.0f} тг — {entry['description']} ({entry['category']})".replace(",", " "))
        
        await message.answer("\n".join(text_msgs))
        await message.answer("Хотите отредактировать категории? Выберите запись:")
        
        # Показываем кнопки для выбора, какую запись редактировать
        for entry in saved_entries:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=cat, callback_data=f"category:{entry['id']}:{cat}") for cat in all_categories()[:4]],
                    [InlineKeyboardButton(text=cat, callback_data=f"category:{entry['id']}:{cat}") for cat in all_categories()[4:8]],
                    [InlineKeyboardButton(text=cat, callback_data=f"category:{entry['id']}:{cat}") for cat in all_categories()[8:]],
                ]
            )
            await message.answer(
                f"#{entry['id']}: {entry['description']} ({entry['category']})\nВыберите правильную категорию:",
                reply_markup=keyboard
            )


@dp.callback_query(lambda callback: callback.data.startswith("category:"))
async def handle_category_callback(callback: CallbackQuery) -> None:
    _, entry_id_str, category = callback.data.split(":", 2)
    entry_id = int(entry_id_str)
    await update_entry_category(entry_id, category)
    await callback.answer(f"Категория обновлена: {category}")
    await callback.message.edit_text(f"{callback.message.text}\n✏️ Категория обновлена: {category}")


@dp.message(F.voice)
async def handle_voice(message: Message) -> None:
    status = await message.answer("🎙 Распознаю голосовое сообщение...")

    tg_file = await bot.get_file(message.voice.file_id)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        local_path = tmp.name
    await bot.download_file(tg_file.file_path, destination=local_path)

    try:
        text = await transcribe_voice(local_path)
    except RuntimeError as e:
        await status.edit_text(str(e))
        return
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

    if not text:
        await status.edit_text("Не удалось распознать речь, попробуй ещё раз.")
        return

    await status.edit_text(f"Распознано: «{text}»")
    await _process_transaction(message, text)


@dp.message(F.text)
async def handle_text(message: Message) -> None:
    await _process_transaction(message, message.text)


async def process_due_recurring_rules() -> None:
    today = date.today()
    rules = await get_due_recurring_rules(today)
    for rule_id, user_id, description, amount, category in rules:
        await add_transaction(user_id, amount, category, description, "expense")
        await advance_recurring_rule(rule_id)


async def main() -> None:
    await init_db()
    await process_due_recurring_rules()
    logger.info("База данных готова, запускаю бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

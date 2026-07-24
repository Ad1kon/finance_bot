# Telegram-бот учёта финансов

Записывает траты текстом или голосом, автоматически определяет категорию
и строит отчёты за месяц (текст + график).

## Возможности

- **Текст**: `кофе 1000`, `1500 такси`, `обед в кафе 3200 тг` — бот сам
  находит сумму и подбирает категорию по ключевым словам.
- **Голос**: отправь голосовое сообщение — оно распознаётся через Groq
  Whisper (`whisper-large-v3`, бесплатный тариф Groq) и обрабатывается
  так же, как текст. Поддерживает русский и казахский.
- **Отчёты**: `/report` — текущий месяц, `/report 2026-06` — конкретный
  месяц. Присылает сводку по категориям и столбчатую диаграмму.
- **Отмена**: `/undo` удаляет последнюю запись.
- Хранилище — SQLite, без внешних зависимостей на сервере.

## Установка

```bash
cd finance_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполни `.env`:

- `BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather).
- `GROQ_API_KEY` — ключ с https://console.groq.com/keys (нужен только
  для распознавания голоса; без него бот работает, просто голосовые
  сообщения обрабатываться не будут).

## Запуск

```bash
python bot.py
```

## Запуск как systemd-сервис (для VPS)

```ini
# /etc/systemd/system/finance-bot.service
[Unit]
Description=Finance Tracker Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/youruser/finance_bot
ExecStart=/home/youruser/finance_bot/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now finance-bot
sudo systemctl status finance-bot
```

## Структура проекта

```
finance_bot/
├── bot.py           # точка входа, обработчики команд/сообщений
├── config.py        # загрузка переменных окружения
├── database.py      # работа с SQLite (aiosqlite)
├── categorizer.py   # правила категоризации по ключевым словам
├── parser.py        # разбор текста трат (регулярки)
├── voice.py         # распознавание голоса через Groq Whisper
├── report.py        # текстовый отчёт + график (matplotlib)
├── requirements.txt
└── .env.example
```

## Как добавить/изменить категории

Отредактируй словарь `CATEGORY_KEYWORDS` в `categorizer.py` — добавь
новую категорию или ключевые слова к существующей. Изменения
применяются сразу после перезапуска бота, без миграций базы.

## Возможные доработки

- Разделение бюджета по нескольким пользователям с общими категориями.
- Лимиты по категориям и уведомления о превышении.
- Экспорт истории в Excel (легко добавить через `openpyxl`).
- Инлайн-кнопки для выбора категории вручную, если авто-определение
  ошиблось.

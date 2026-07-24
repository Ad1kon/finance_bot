## Plan: Extend finance bot with manual correction, limits, income, export, and recurring entries

### Goal
Add the requested financial features while keeping the current simple Telegram UX and SQLite-based architecture.

### Recommended implementation order
1. Extend the data model in database.py
   - Add an entry type field for income vs expense.
   - Store a manual category override per entry.
   - Add tables for category limits and recurring rules.
   - Keep the existing expenses table compatible by adding new columns and default values.

2. Update parsing and categorization flow
   - In parser.py, support explicit income syntax such as "+150000 зарплата" and optional negative/positive sign handling.
   - In categorizer.py, keep auto-detection, but allow the bot to reuse a manually selected category for a specific record.

3. Add interactive correction for misclassified transactions
   - In bot.py, after a successful record, send an inline keyboard with category options.
   - Handle callback queries so the user can change the category without re-entering the text.
   - Store the override and keep the original message context linked to that transaction.

4. Add category limits and notifications
   - Introduce monthly limits per category (for example, Transport: 15000 tng/month).
   - Compute current usage from the database and send warnings at 80% and 100% thresholds.
   - Provide a simple command such as /limits or /setlimit for management.

5. Add income support and balance-aware reporting
   - Update report.py and the report command to show income, expenses, and balance.
   - Keep the existing monthly category breakdown, but make it work for both expense and income entries.

6. Add Excel export
   - In report.py or a new export module, generate an .xlsx file for a chosen period.
   - Add a /export command in bot.py that sends the file to the user.
   - Support a date range or month filter from the command input.

7. Add recurring transactions
   - Create a recurring rules table and a small scheduler layer (either a simple startup-based loop or APScheduler).
   - Support rules like monthly rent, utilities, subscriptions, and generate the transaction automatically on the next due date.
   - Provide a lightweight command such as /recurring add and /recurring list.

### Relevant files
- bot.py — main bot flow, message handlers, commands, callback handlers.
- database.py — SQLite schema, inserts, reads, aggregates, limits, recurring rules.
- parser.py — parsing amount/description and distinguishing income from expense.
- categorizer.py — category detection and manual override support.
- report.py — monthly report text, charts, and Excel export.
- config.py — environment/config defaults for export paths or feature flags.
- requirements.txt — add Excel and scheduling dependencies.
- README.md — update documentation and command reference.

### New files likely to add
- handlers/ — if you want to split callback handlers and command handlers out of the main bot file.
- recurring.py — for recurring transaction handling.

### Verification plan
1. Add a small regression test or manual checklist for parsing income and expense messages.
2. Verify that category correction updates the stored category without re-entering the transaction.
3. Verify that limit warnings appear only at the correct threshold.
4. Verify that /report shows a balance and /export creates a valid Excel file.
5. Verify that recurring rules are created and inserted once per scheduled period.

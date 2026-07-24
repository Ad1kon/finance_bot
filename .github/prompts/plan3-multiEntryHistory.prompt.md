## Plan: Support multiple entries in one message and add monthly history view

### Goal
Make the bot correctly understand messages with several separate expenses or incomes in one text, and add a command to show all recorded entries from the last month with date, time, amount, category, and description.

### Scope
1. Improve parsing for multiple entries in one message
   - If a user sends something like “такси 2000, кофе 3000”, the parser should split it into two separate entries.
   - Each part should be parsed independently so the correct category is assigned to the correct amount.
   - Preserve support for single-entry messages like “кофе 1000”, “+150000 зарплата”, and “обед 3200 тг”.

2. Update the bot flow to process multiple records
   - In bot.py, replace the single-entry flow with a list-based flow.
   - For each parsed item, save it separately, check category limits, and notify the user accordingly.
   - Ensure the bot does not mix amounts and categories across entries.

3. Add a monthly history command
   - Implement a command such as /history or /history 2026-07.
   - Show a list of transactions from the selected month (default: last month or current month).
   - Include:
     - date
     - time without seconds
     - amount
     - category
     - description

4. Extend the database layer
   - Add a helper to fetch transactions for a chosen period.
   - Keep the existing monthly report logic intact while supporting the new history view.

5. Add tests
   - Cover parsing of a multi-entry message into multiple transactions.
   - Cover the history query output format if needed.

### Files to change
- parser.py — split one message into multiple parsed transactions
- bot.py — process multiple parsed entries and add the history command
- database.py — add a query for monthly history entries
- tests/test_parser.py — add regression tests for multi-entry parsing

### Verification plan
- Verify that “такси 2000, кофе 3000” creates two separate records.
- Verify that each record gets the correct category.
- Verify that /history shows the recent entries with date, time, amount, category, and description.

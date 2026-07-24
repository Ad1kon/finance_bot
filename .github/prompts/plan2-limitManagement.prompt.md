## Plan: Improve category limits and add limit management commands

### Goal
Make category limits useful and actionable: users should be notified when a limit is reached or exceeded, and they should be able to view, update, and remove limits easily.

### Scope
1. Fix the current limit-checking flow
   - When a new expense is recorded, check whether it belongs to a category with an active monthly limit.
   - If the current spending reaches 80%, notify the user that the limit is approaching.
   - If spending reaches 100%, notify the user that the limit is already reached.
   - If spending exceeds the limit, send a clear warning and a practical recommendation to reduce spending.

2. Add limit management commands
   - /limits — show all active limits with current spending and remaining amount.
   - /setlimit "Категория" 15000 — create or update a limit.
   - /removelimit "Категория" — remove an existing limit.
   - Optionally /updatelimit as an alias for /setlimit if a clearer UX is desired.

3. Improve the database layer
   - Keep limit storage in the database with user_id, category, limit_amount, and maybe created_at.
   - Support update and delete operations cleanly.
   - Make it easy to retrieve current monthly usage per category.

4. Improve user-facing messages
   - Use clearer wording such as:
     - “⚠️ Лимит по категории Транспорт достиг 80%”
     - “🚨 Лимит по категории Транспорт уже исчерпан”
     - “⚠️ Вы превысили лимит по категории Транспорт. Рекомендуем сократить расходы или перенести часть трат на другой период.”

5. Make the flow feel integrated
   - The limit check should run automatically when a new expense is saved.
   - The /limits command should show the current status of each limit at a glance.
   - Users should be able to manage limits without editing the database manually.

### Files to change
- bot.py — add command handlers and limit-warning logic
- database.py — add or adjust limit CRUD operations
- README.md — document the new limit-management commands

### Verification plan
- Create a limit for a category.
- Record expenses that reach 80%, 100%, and exceed the limit.
- Verify that the bot sends the correct warning messages.
- Verify that /limits lists the limits correctly.
- Verify that /setlimit updates an existing limit and /removelimit removes it.

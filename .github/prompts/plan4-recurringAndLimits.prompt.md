## Plan: Expand recurring payments, categorization, manual correction, and reporting

### Goal
Make the bot smarter and more practical for real-life finance tracking by integrating recurring payments into reports, improving category detection, allowing manual category correction for multi-entry messages, supporting recurring-payment editing/removal, normalizing category names for limits, and showing limits and recurring payments in the monthly report.

### Scope
1. Include recurring payments in reports
   - Add recurring payments to the monthly report output.
   - Show the recurring item name, amount, category, and next due date.
   - Use database data from recurring_rules.

2. Improve recurring payment categorization
   - Apply the same categorization logic used for regular expenses to recurring payments.
   - Examples:
     - apple / subscription / подписка → category such as Подписки or Связь и подписки
     - rent / аренда → category such as Дом и коммуналка
   - Expand the category keyword dictionary with more words, service names, and synonyms.

3. Improve category detection coverage
   - Add more keywords to the base category dictionary.
   - Include Russian, English, and common service names.
   - Cover popular spending patterns for food, transport, subscriptions, utilities, shopping, entertainment, health, and education.

4. Add manual category correction for multi-entry messages
   - When the user sends several records in one message, the bot should allow manual correction for any entry that was misclassified.
   - After saving the entries, present inline category-selection options for each parsed item.
   - Allow changing the category without re-entering the whole message.

5. Add recurring-payment editing and removal
   - Support commands such as:
     - /recurring list
     - /recurring edit <id> <amount> <category>
     - /recurring remove <id>
   - Implement the database helpers to fetch, update, and delete recurring rules.

6. Normalize category names for limits and category management
   - Make /setlimit and /removelimit work regardless of case.
   - Normalize categories so “Транспорт”, “транспорт”, and similar variants refer to the same internal category.
   - Apply the same normalization wherever category names are used: limits, manual correction, reports, recurring payments, and storage.

7. Extend the monthly report with limits and recurring payments
   - In the monthly report, include:
     - recurring payments section
     - current limit status section
   - Show how close each category is to its limit and whether it is exceeded.

### Files to change
- categorizer.py — expand keyword dictionaries and add category normalization helpers
- database.py — add recurring rule update/delete helpers and limit/category normalization support
- bot.py — add manual category correction flow, recurring-edit/remove commands, and better limit handling
- report.py — include recurring payments and limit status in the report
- parser.py — keep multi-entry parsing compatible with the new correction flow

### Verification plan
- Verify that recurring payments appear in the monthly report.
- Verify that recurring payments are classified into the right category.
- Verify that /setlimit works for different casing of the same category.
- Verify that manual category changes work for entries parsed from a multi-entry message.
- Verify that recurring items can be edited and removed.
- Verify that the monthly report shows both recurring payments and limit status.

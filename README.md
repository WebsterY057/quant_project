# Light Read

This repository stores a reusable Xiaohongshu book-reading content workflow.

## Contents

- `book_series/`: book ledgers and generated Xiaohongshu post drafts.
- `agents/`: role prompts for book knowledge extraction, social context mapping, and post writing.
- `skills/book-xiaohongshu-series/`: Codex skill for maintaining the ledger and generating the next post.

## Workflow

1. Create or update a book ledger under `book_series/<book_slug>.md`.
2. Generate the next post from the first `pending` topic.
3. Save drafts under `book_series/posts/<book_slug>/<topic_id>_<YYYY-MM-DD>.md`.
4. Update the ledger with publication status, date, and draft path.

The skill contract is documented in `skills/book-xiaohongshu-series/SKILL.md`.

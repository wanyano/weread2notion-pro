# Pro 2026 compatibility branch

This is an unverified upgrade of the existing Pro database layout.

Changes: Notion Data Sources API, optional WeRead API-key gateway, local package installation, manual-only Actions, and non-deleting synchronization. The old cookie path remains available.

Before the first live run: export the existing Notion workspace, verify integration access, and test against a copy of the Pro root page. Configure NOTION_TOKEN, NOTION_PAGE, and either WEREAD_API_KEY or the legacy cookie secrets in GitHub Actions. Never commit credentials.

Existing secrets in the old Notion Settings database require manual cleanup. The new code does not write them.

Known limitations: Gateway notebook mode does not list the entire bookshelf. Reading-time and heatmap updates cannot yet use the Gateway pathway. The real authentication result, new Notion database schemas, and idempotence need verification. Workflows are manual-only until reviewed.


## Full bookshelf recovery (2026 books)

The previous API-key implementation read only `/user/notebooks` and therefore
could never import books without notes. This branch now calls the official
`/shelf/sync` Gateway endpoint and unions its `books[]` with notebook books
by `bookId`. Albums/audiobooks are counted in the preview but are not
automatically imported as ordinary ebooks. Article collection `mp` is not a book.

Run `weread note sync` manually from the repair branch:

- `preview` (default): show `FULL_SHELF_AUDIT` and `MISSING_BOOK` log
  lines; does **not** create missing book pages or run note sync.
- `import`: create missing books by ID, then run note sync. Existing book pages
  are not intentionally rewritten during this bookshelf import, but the note
  sync phase can write highlights; back up first.
- `notes`: run note sync only, without touching the bookshelf.

Please compare the preview against your current WeRead shelf, especially books
added during 2026. Review any names not recognized. No automatic schedules are
enabled on this branch. Do not merge until the first import has been verified.

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


## Reading time restoration (official WeRead Gateway)

The `read time sync` workflow is independent of heatmap generation. The
previous workflow failed in `github_heatmap` before `read_time` ran; it also
disabled API-key reading-time operations. This branch now queries the official
`/readdata/detail` endpoint in `monthly` mode using `baseTime` at each
month's start (Asia/Shanghai). Monthly `readTimes` is keyed by day and measured
in **seconds**, not minutes. The current year is the default; select a prior
year to restore historical records. The script reconciles the existing Pro
`日` database and its `周`, `月`, `年` relations.

Manual workflow: `read time sync` on `fix/pro-2026-safe-sync`.

1. Choose `mode=preview` (default), and optionally `year=2026`. Preview
   makes no Notion changes, including the `设置` database.
2. Inspect `READ_TIME_MONTH` and `READ_TIME_AUDIT` logs. Missing or
   ambiguous daily buckets stop the job instead of guessing.
3. Back up the Pro database. Choose `mode=import` only after review.
   The importer creates only missing positive-duration days or updates
   changed dates. It never deletes dates or replaces old days with zero.
4. Run `preview` again and confirm `create=0 update=0` for idempotence.
5. Repeat for previous calendar years as required.

Heatmap rendering and updating existing heatmap blocks remain separate tasks
and are **not** enabled by this change. Do not run old main-branch schedules
against the same Notion databases during testing. Credentials should be stored
only in GitHub Secrets; never include them in issue comments or logs.

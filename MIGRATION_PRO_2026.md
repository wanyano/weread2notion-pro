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


## Reading records and heatmap recovery

The existing Pro layout distinguishes three data categories:
- `日`: aggregate reading seconds per calendar day, restored by `read time sync`.
- `书架.阅读时长`: per-book **cumulative** seconds, available from the official
  `/book/getprogress` Gateway API. A non-destructive batch preview/import is now available.
- `阅读记录`: historical **per-book per-day** durations. The documented Gateway
  endpoints do NOT provide a verifiable book-by-day history. Do not populate
  this database with extrapolated data or daily totals falsely attributed
  to books. Existing historical entries remain intact.

On the pre-existing `read time sync` Actions workflow, select the repair
branch `fix/pro-2026-safe-sync` and choose:
- `book_preview`: audit a batch of up to 100 shelf books; optional `offset`
  (starting 0) and `limit` (default 40). No Notion writes.
- `book_import`: only increase the existing `书架.阅读时长` values for books
  where the official API reports a higher cumulative duration. It does NOT
  write to `阅读记录`, change existing reading details, or zero older values.
- `heatmap_preview`: read the existing `日` database and render a full-year
  SVG into a downloadable Actions artifact. No Notion writes or Git commits.
- `heatmap_publish`: render SVG and commit `OUT_FOLDER/weread_YEAR.svg`
  to the repair branch, then update the pre-existing Notion heatmap embed to
  reference that exact commit. Requires GitHub contents:write permission.
  It does not overwrite old SVG files or insert a new embed if the existing
  placeholder is missing.

For heatmap restoration, run `heatmap_preview` for 2026, download/review the
artifact and the `HEATMAP_AUDIT` line, and only then run `heatmap_publish`.
For cumulative book time, start with `book_preview` offset 0, limit 40, and
confirm the audit before `book_import`; repeat batches with offsets 40, 80,
120, etc. No automatic scheduling is enabled on this branch.

If the old `main` branch still has a scheduled workflow, disable or
supersede it before enabling any new schedule to avoid conflicting writes.


## Weekly safe synchronization

The repair branch contains `.github/workflows/weekly_safe_sync.yml`. It is
scheduled for Monday 05:17 Asia/Shanghai (Sunday 21:17 UTC) and performs these
steps serially:

1. increment the current year's daily reading-time records;
2. render and commit the current-year heatmap, then update the existing embed;
3. increment cumulative reading time for every ebook already in the Notion shelf.

Daily and per-book durations are monotonic: missing/zero/lower source values
never clear or reduce existing Notion history. All workflows that can write to
Notion share the `weread-notion-sync` concurrency group and queue rather than
cancel an in-progress write.

GitHub only runs scheduled workflows from the repository's default branch.
Therefore the weekly schedule is intentionally **not active while this remains
only a draft repair branch**. Manual dispatch is allowed on
`fix/pro-2026-safe-sync` for controlled validation. The current `main`
branch still contains the two legacy three-hour schedules; those are replaced
only after this PR is reviewed and merged, or they must be disabled manually in
GitHub Actions. This draft does not modify `main` directly.


## Existing book status and progress

The safe book reconciliation also reads `progress`, `finishTime`, and
`recordReadingTime` from WeRead `/book/getprogress` for every ebook already
present in the Notion shelf.

Updates are monotonic:

- `想读 -> 在读 -> 已读` is allowed; status is never downgraded.
- A nonzero `finishTime` or 100% progress promotes the book to `已读`.
- A finished book is promoted to 100% progress.
- Reading progress and cumulative reading time only increase.
- Only `阅读状态`, `阅读进度`, and `阅读时长` are patched.
- Preview mode reports counts and never modifies a Notion page.

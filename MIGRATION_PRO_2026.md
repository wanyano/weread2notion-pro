# Pro 2026 compatibility branch

This is an unverified upgrade of the existing Pro database layout.

Changes: Notion Data Sources API, optional WeRead API-key gateway, local package installation, manual-only Actions, and non-deleting synchronization. The old cookie path remains available.

Before the first live run: export the existing Notion workspace, verify integration access, and test against a copy of the Pro root page. Configure NOTION_TOKEN, NOTION_PAGE, and either WEREAD_API_KEY or the legacy cookie secrets in GitHub Actions. Never commit credentials.

Existing secrets in the old Notion Settings database require manual cleanup. The new code does not write them.

Known limitations: Gateway notebook mode does not list the entire bookshelf. Reading-time and heatmap updates cannot yet use the Gateway pathway. The real authentication result, new Notion database schemas, and idempotence need verification. Workflows are manual-only until reviewed.

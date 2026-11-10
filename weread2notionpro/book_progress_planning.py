"""Pure safety helpers for cumulative per-book reading-time sync."""


def select_book_batch(book_ids, offset, limit):
    """Select a manual batch, or every remaining book when limit is zero."""
    if offset < 0 or limit < 0 or limit > 100:
        raise ValueError("Offset must be nonnegative; limit must be 0-100")
    return book_ids[offset:] if limit == 0 else book_ids[offset:offset + limit]


def cumulative_update(source, existing):
    """Return a monotonic replacement value, or None when history is kept."""
    if (
        isinstance(source, bool)
        or not isinstance(source, (int, float))
        or source < 0
        or int(source) != source
    ):
        raise ValueError("Invalid cumulative reading duration from WeRead")
    if existing is not None and (
        isinstance(existing, bool)
        or not isinstance(existing, (int, float))
        or existing < 0
        or int(existing) != existing
    ):
        raise ValueError("Invalid existing cumulative book duration in Notion")
    source = int(source)
    current = int(existing or 0)
    return source if source > current else None


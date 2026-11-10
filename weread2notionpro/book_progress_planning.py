"""Pure safety helpers for monotonic per-book state synchronization."""


STATUS_RANK = {"想读": 0, "在读": 1, "已读": 2}


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


def book_state_update(source, existing):
    """Plan safe field changes from one /book/getprogress response.

    Reading time and progress can only increase. Reading status can only move
    from 想读 to 在读 to 已读. A finishTime is authoritative and forces 100%.
    """
    if not isinstance(source, dict):
        raise ValueError("Invalid WeRead book progress payload")
    if not isinstance(existing, dict):
        raise ValueError("Invalid existing Notion book state")

    progress = source.get("progress")
    if progress is None:
        progress = 0
    if (
        isinstance(progress, bool)
        or not isinstance(progress, (int, float))
        or progress < 0
        or progress > 100
    ):
        raise ValueError("Invalid reading progress from WeRead")

    finish_time = source.get("finishTime") or 0
    if (
        isinstance(finish_time, bool)
        or not isinstance(finish_time, (int, float))
        or finish_time < 0
    ):
        raise ValueError("Invalid finish time from WeRead")

    seconds = source.get("recordReadingTime")
    seconds_change = None
    if seconds is not None:
        seconds_change = cumulative_update(seconds, existing.get("readingTime"))

    finished = bool(finish_time) or progress >= 100
    source_status = (
        "已读"
        if finished
        else "在读"
        if progress > 0 or (seconds or 0) > 0
        else "想读"
    )
    source_progress = 1.0 if finished else float(progress) / 100

    current_progress = existing.get("readingProgress")
    if current_progress is not None and (
        isinstance(current_progress, bool)
        or not isinstance(current_progress, (int, float))
        or current_progress < 0
        or current_progress > 1
    ):
        raise ValueError("Invalid existing Notion reading progress")
    progress_change = (
        source_progress
        if source_progress > float(current_progress or 0)
        else None
    )

    current_status = existing.get("status")
    status_change = None
    if source_status == "已读" and current_status != "已读":
        # Completion from WeRead is authoritative even for a custom old label.
        status_change = "已读"
    elif current_status is None and source_status != "想读":
        status_change = source_status
    elif (
        current_status in STATUS_RANK
        and STATUS_RANK[source_status] > STATUS_RANK[current_status]
    ):
        status_change = source_status

    return {
        "reading_time": seconds_change,
        "reading_progress": progress_change,
        "status": status_change,
        "source_status": source_status,
    }


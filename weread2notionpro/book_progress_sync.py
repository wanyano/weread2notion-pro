"""Safely reconcile cumulative reading time for books already in Notion."""
import os

from weread2notionpro.book_progress_planning import (
    book_state_update,
    select_book_batch,
)
from weread2notionpro.notion_helper import NotionHelper
from weread2notionpro.weread_api import WeReadApi


def prepare_changes(api, notion_books, ordered_ids):
    changes, preserved, missing = [], 0, 0
    time_updates = progress_updates = status_updates = 0
    for index, book_id in enumerate(ordered_ids, 1):
        record = notion_books.get(book_id)
        if not record:
            missing += 1
            continue
        data = api.gateway("/book/getprogress", bookId=book_id)
        book = data.get("book") or {}
        planned = book_state_update(book, record)
        if not any(
            planned[key] is not None
            for key in ("reading_time", "reading_progress", "status")
        ):
            preserved += 1
            continue
        time_updates += planned["reading_time"] is not None
        progress_updates += planned["reading_progress"] is not None
        status_updates += planned["status"] is not None
        changes.append({
            "page_id": record["pageId"],
            "book_id": book_id,
            **planned,
        })
        if index % 20 == 0:
            print(f"BOOK_PROGRESS_READ: {index}/{len(ordered_ids)}")
    return {
        "changes": changes,
        "preserved": preserved,
        "missing": missing,
        "time_updates": time_updates,
        "progress_updates": progress_updates,
        "status_updates": status_updates,
    }


def main():
    mode = os.environ.get("BOOK_PROGRESS_MODE", "preview").lower()
    if mode not in ("preview", "import"):
        raise ValueError("Invalid BOOK_PROGRESS_MODE")
    os.environ["NOTION_READ_ONLY"] = "true"
    api = WeReadApi()
    if not api.api_key:
        raise ValueError("WEREAD_API_KEY is required")
    helper = NotionHelper()
    notion_books = helper.get_all_book()
    shelf = api.get_bookshelf()
    ids = list(dict.fromkeys(
        str(item["bookId"])
        for item in shelf.get("books", [])
        if item.get("bookId")
    ))
    offset = int(os.environ.get("BOOK_PROGRESS_OFFSET") or 0)
    limit = int(os.environ.get("BOOK_PROGRESS_LIMIT") or 40)
    subset = select_book_batch(ids, offset, limit)
    plan = prepare_changes(api, notion_books, subset)
    print(
        f'BOOK_PROGRESS_AUDIT: mode={mode} offset={offset} batch={len(subset)} '
        f'total_shelf_books={len(ids)} update={len(plan["changes"])} '
        f'time={plan["time_updates"]} progress={plan["progress_updates"]} '
        f'status={plan["status_updates"]} preserved={plan["preserved"]} '
        f'missing_notion={plan["missing"]}'
    )
    if mode == "preview":
        print("BOOK_PROGRESS_PREVIEW_ONLY: no Notion book fields modified")
        return
    for item in plan["changes"]:
        properties = {}
        if item["reading_time"] is not None:
            properties["阅读时长"] = {"number": item["reading_time"]}
        if item["reading_progress"] is not None:
            properties["阅读进度"] = {"number": item["reading_progress"]}
        if item["status"] is not None:
            properties["阅读状态"] = {"status": {"name": item["status"]}}
        helper.update_book_page(
            page_id=item["page_id"],
            properties=properties,
        )
    print(
        f'BOOK_PROGRESS_IMPORT_COMPLETED: pages={len(plan["changes"])} '
        f'time={plan["time_updates"]} progress={plan["progress_updates"]} '
        f'status={plan["status_updates"]}'
    )


if __name__ == "__main__":
    main()


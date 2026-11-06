"""Safe per-book *cumulative* reading time reconciliation.

This updates the 书架.阅读时长 number only. The official Gateway's
/book/getprogress cannot reconstruct book-by-book historical daily records, so
this module never writes into the separate 阅读记录 database.
"""
import os
from weread2notionpro.weread_api import WeReadApi
from weread2notionpro.notion_helper import NotionHelper


def prepare_changes(api, notion_books, ordered_ids):
    changes, preserved, ignored, missing = [], 0, 0, 0
    for index, book_id in enumerate(ordered_ids, 1):
        record=notion_books.get(book_id)
        if not record:
            missing+=1
            continue
        data=api.gateway("/book/getprogress",bookId=book_id)
        book=data.get("book") or {}
        source=book.get("recordReadingTime")
        if source is None:
            ignored+=1
            continue
        if isinstance(source,bool) or not isinstance(source,(int,float)) or source<0 or int(source)!=source:
            raise ValueError("Invalid cumulative reading duration from WeRead")
        source=int(source)
        existing=record.get("readingTime")
        if existing is not None and (not isinstance(existing,(int,float)) or existing<0):
            raise ValueError("Invalid existing cumulative book duration in Notion")
        current=int(existing or 0)
        if source<=current:
            preserved+=1
            continue
        changes.append({"page_id":record["pageId"],"seconds":source,"book_id":book_id})
        if index % 20 == 0:
            print(f"BOOK_PROGRESS_READ: {index}/{len(ordered_ids)}")
    return {"changes":changes,"preserved":preserved,"ignored":ignored,"missing":missing}


def main():
    mode=os.environ.get("BOOK_PROGRESS_MODE","preview").lower()
    if mode not in ("preview","import"):
        raise ValueError("Invalid BOOK_PROGRESS_MODE")
    os.environ["NOTION_READ_ONLY"]="true"
    api=WeReadApi()
    if not api.api_key:
        raise ValueError("WEREAD_API_KEY is required")
    helper=NotionHelper()
    notion_books=helper.get_all_book()
    shelf=api.get_bookshelf()
    ids=list(dict.fromkeys(str(x["bookId"]) for x in shelf.get("books",[]) if x.get("bookId")))
    offset=int(os.environ.get("BOOK_PROGRESS_OFFSET") or 0)
    limit=int(os.environ.get("BOOK_PROGRESS_LIMIT") or 40)
    if offset<0 or not 1<=limit<=100:
        raise ValueError("Offset must be nonnegative; limit between 1 and 100")
    subset=ids[offset:offset+limit]
    plan=prepare_changes(api,notion_books,subset)
    print(
        f'BOOK_PROGRESS_AUDIT: mode={mode} offset={offset} batch={len(subset)} '
        f'total_shelf_books={len(ids)} update={len(plan["changes"])} '
        f'preserved={plan["preserved"]} no_source={plan["ignored"]} '
        f'missing_notion={plan["missing"]}'
    )
    if mode=="preview":
        print("BOOK_PROGRESS_PREVIEW_ONLY: no Notion page changes")
        return
    for item in plan["changes"]:
        helper.update_book_page(
            page_id=item["page_id"],
            properties={"阅读时长":{"number":item["seconds"]}},
        )
    print(f'BOOK_PROGRESS_IMPORT_COMPLETED: updated={len(plan["changes"])}')


if __name__=="__main__":
    main()

"""Pure, non-destructive sync planning for the Pro bookshelf.

The WeRead notebook list contains books with annotations only. Use /shelf/sync
as the authoritative source of *shelved* ebooks, and union notebook books so
that annotated books removed from the shelf are still retained.
"""


def plan_bookshelf(shelf, notebooks, existing_ids):
    if not isinstance(shelf, dict) or not isinstance(shelf.get("books"), list):
        raise ValueError("WeRead /shelf/sync response is missing books[]")
    if not isinstance(notebooks, list):
        raise ValueError("WeRead notebook list is not an array")

    ids = []
    metadata = {}
    seen = set()

    for source in (shelf["books"], notebooks):
        for record in source:
            if not isinstance(record, dict) or not record.get("bookId"):
                continue
            book_id = str(record["bookId"])
            if book_id not in seen:
                seen.add(book_id)
                ids.append(book_id)
            info = record.get("book") or record
            if book_id not in metadata or source is shelf["books"]:
                metadata[book_id] = info

    known = set(str(x) for x in existing_ids if x)
    missing = [book_id for book_id in ids if book_id not in known]

    return {
        "book_ids": ids,
        "missing_book_ids": missing,
        "metadata": metadata,
        "shelf_ebook_count": len(shelf["books"]),
        "shelf_album_count": len(shelf.get("albums") or []),
        "shelf_has_mp": bool(shelf.get("mp")),
        "notebook_count": len(notebooks),
    }

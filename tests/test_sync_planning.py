"""Credential-free tests for bookshelf reconciliation and safety."""
import unittest
from weread2notionpro.sync_planning import plan_bookshelf


class BookshelfPlanningTests(unittest.TestCase):
    def test_full_shelf_adds_unannotated_book(self):
        shelf = {"books": [
            {"bookId": "new2026", "title": "2026 new book"},
            {"bookId": "old", "title": "Existing"},
        ], "albums": [{"albumInfo": {"albumId": "a1"}}]}
        notebooks = [{"bookId": "old", "sort": 4},
                     {"bookId": "annotated_old", "book": {"title": "Archived with notes"}}]
        result = plan_bookshelf(shelf, notebooks, {"old"})
        self.assertEqual(result["missing_book_ids"], ["new2026", "annotated_old"])
        self.assertEqual(result["shelf_ebook_count"], 2)
        self.assertEqual(result["shelf_album_count"], 1)
        self.assertEqual(result["metadata"]["new2026"]["title"], "2026 new book")

    def test_deduplicates_overlapping_books(self):
        shelf = {"books": [{"bookId": "same"}, {"bookId": "same"}]}
        notebooks = [{"bookId": "same"}]
        result = plan_bookshelf(shelf, notebooks, [])
        self.assertEqual(result["book_ids"], ["same"])
        self.assertEqual(result["missing_book_ids"], ["same"])

    def test_fails_closed_when_shelf_missing(self):
        with self.assertRaises(ValueError):
            plan_bookshelf({"errcode": 123}, [], [])


if __name__ == "__main__":
    unittest.main()

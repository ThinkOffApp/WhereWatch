"""Unit tests for the parts of wherewatch_base.py that need no model or server.

Run: python3 -m unittest base/test_base.py
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wherewatch_base as ww  # noqa: E402


class PeopleFilter(unittest.TestCase):
    def test_people_are_caught(self):
        for s in ["person", "a woman on the couch", "on the person&#x27;s head",
                  "being worn", "held in her hand", "the kids", "someone's lap",
                  "his pocket", "selfie"]:
            self.assertTrue(ww.PEOPLE.search(s), s)

    def test_places_and_things_pass(self):
        for s in ["keys", "headphones", "headset", "the arm of the sofa",
                  "left armrest", "handbag", "hallway table", "kitchen counter",
                  "beside the bowl", "other side of the desk", "shelf"]:
            self.assertFalse(ww.PEOPLE.search(s), s)


class Matching(unittest.TestCase):
    def test_question_words_are_dropped(self):
        self.assertEqual(ww.words("Where are my keys?"), ["keys"])

    def test_singular_plural_and_aliases(self):
        self.assertTrue(ww.match("key", json.dumps(["keychain"]), ["keys"]))
        self.assertTrue(ww.match("keys", "[]", ["key"]))
        self.assertTrue(ww.match("wallet", json.dumps(["purse"]), ["purse"]))
        self.assertFalse(ww.match("wallet", "[]", ["keys"]))


class Clean(unittest.TestCase):
    def test_markup_cannot_reach_the_page(self):
        self.assertNotIn("<", ww.clean("<img src=x onerror=alert(1)>"))

    def test_length_is_capped(self):
        self.assertEqual(len(ww.clean("x" * 500, 40)), 40)


if __name__ == "__main__":
    unittest.main()

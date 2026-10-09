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


class FaceBlur(unittest.TestCase):
    def test_boxes_scale_pad_and_clamp(self):
        (x1, y1, x2, y2), = ww.face_boxes({"people": True, "faces": [[400, 400, 600, 600]]}, 1000, 500)
        self.assertLess(x1, 400)
        self.assertGreater(x2, 600)
        self.assertLess(y1, 200)
        self.assertGreater(y2, 300)
        (_, _, x2, y2), = ww.face_boxes({"people": True, "faces": [[900, 900, 1000, 1000]]}, 100, 100)
        self.assertEqual((x2, y2), (100, 100))

    def test_people_without_usable_boxes_fails_closed(self):
        self.assertIsNone(ww.face_boxes({"people": True, "faces": []}, 10, 10))
        self.assertIsNone(ww.face_boxes({"people": True, "faces": [["x"], [1, 2]]}, 10, 10))
        self.assertEqual(ww.face_boxes({"people": False, "faces": []}, 10, 10), [])

    def test_answers_of_the_wrong_shape_fail_closed(self):
        for bad in [None, [], "no faces", {}, {"faces": []}, {"people": "no", "faces": []},
                    {"people": False}, {"people": False, "faces": "none"},
                    {"people": False, "faces": [["x"]]}]:
            self.assertIsNone(ww.face_boxes(bad, 10, 10), bad)

    def test_one_bad_box_rejects_the_whole_answer(self):
        good = [100, 100, 200, 200]
        for bad in [[float("nan"), 0, 10, 10], [0, 0, float("inf"), 10], [-5, 0, 10, 10],
                    [0, 0, 1001, 10], [5, 5, 5, 50], [1, 2, 3], "box", [1, 2, "x", 4]]:
            self.assertIsNone(ww.face_boxes({"people": True, "faces": [good, bad]}, 10, 10), bad)

    def _image(self, path):
        from PIL import Image
        im = Image.new("RGB", (200, 100))
        for x in range(200):
            for y in range(100):
                im.putpixel((x, y), (x % 2 * 255, y % 2 * 255, 128))  # sharp checkerboard
        im.save(path)

    def test_only_the_face_region_changes(self):
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.png")
            self._image(p)
            before = Image.open(p).copy()
            self.assertEqual(ww.blur_faces(p, {"people": True, "faces": [[400, 300, 600, 700]]}), 1)
            after = Image.open(p)
            self.assertNotEqual(before.getpixel((100, 50)), after.getpixel((100, 50)))  # face centre
            self.assertEqual(before.getpixel((5, 5)), after.getpixel((5, 5)))          # far corner

    def test_failed_face_check_blurs_everything(self):
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.png")
            self._image(p)
            before = Image.open(p).copy()
            self.assertEqual(ww.blur_faces(p, None), -1)
            self.assertNotEqual(before.getpixel((5, 5)), Image.open(p).getpixel((5, 5)))


class PublishFlow(unittest.TestCase):
    """The unblurred original must never be in the served photos/ folder."""

    def setUp(self):
        import tempfile
        from PIL import Image
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        for sub in ("inbox", "photos", "staging"):
            os.makedirs(os.path.join(d, sub))
        self.args = type("A", (), {"data": d, "vision": "x", "model": "m", "timeout": 1})()
        self.store = ww.Store(os.path.join(d, "i.sqlite"))
        self.src = os.path.join(d, "inbox", "p.png")
        Image.new("RGB", (40, 20), (200, 10, 10)).save(self.src)
        self.real = ww.ask_vision

    def tearDown(self):
        ww.ask_vision = self.real
        self.tmp.cleanup()

    def photos(self):
        return os.listdir(os.path.join(self.tmp.name, "photos"))

    def test_nothing_is_served_until_blurred_and_indexed(self):
        seen = []

        def fake(url, model, path, timeout, prompt=ww.PROMPT):
            seen.append((self.photos(), os.path.dirname(path)))
            if prompt is ww.FACE_PROMPT:
                return {"people": False, "faces": []}
            return {"place": "desk", "objects": [{"name": "keys", "relative_position": "left"}]}
        ww.ask_vision = fake
        ww.index_photo(self.store, self.args, self.src)
        for photos_then, workdir in seen:
            self.assertEqual(photos_then, [])                     # nothing published yet
            self.assertTrue(workdir.endswith("staging"))          # model reads the private copy
        self.assertEqual(self.photos(), ["p.png"])
        self.assertFalse(os.path.exists(self.src))                # original gone only at the end
        self.assertEqual(self.store.q("SELECT name FROM sightings"), [("keys",)])

    def test_crash_mid_way_leaves_only_the_private_original(self):
        class Crash(BaseException):
            pass

        def boom(*a, **k):
            raise Crash()
        ww.ask_vision = boom
        with self.assertRaises(Crash):
            ww.index_photo(self.store, self.args, self.src)
        self.assertEqual(self.photos(), [])
        self.assertTrue(os.path.exists(self.src))                 # retried on restart
        self.assertEqual(self.store.q("SELECT COUNT(*) FROM photos"), [(0,)])

    def test_retention_keeps_the_row_when_the_file_cannot_be_deleted(self):
        p = os.path.join(self.tmp.name, "photos", "old.png")
        open(p, "wb").close()
        self.store.q("INSERT INTO photos(file,taken_at) VALUES('old.png','2000-01-01T00:00:00')")
        real_remove = os.remove

        def stuck(path):
            raise PermissionError("busy")
        ww.os.remove = stuck
        try:
            ww.prune(self.store, self.args)
        finally:
            ww.os.remove = real_remove
        self.assertEqual(self.store.q("SELECT file FROM photos"), [("old.png",)])  # retried later
        ww.prune(self.store, self.args)
        self.assertEqual(self.store.q("SELECT COUNT(*) FROM photos"), [(0,)])
        self.assertFalse(os.path.exists(p))

    def test_rotated_phone_photo_is_upright_before_the_model_sees_it(self):
        from PIL import Image
        im = Image.new("RGB", (40, 20))
        exif = im.getexif()
        exif[0x0112] = 6  # "rotate 90": the camera stored it sideways
        jpg = os.path.join(self.tmp.name, "inbox", "r.jpg")
        im.save(jpg, exif=exif)
        out = os.path.join(self.tmp.name, "staging", "r.jpg")
        ww.normalize(jpg, out)
        with Image.open(out) as n:
            self.assertEqual(n.size, (20, 40))
            self.assertNotIn(0x0112, n.getexif())


class Recap(unittest.TestCase):
    """The day recap: model-written when trustworthy, plain otherwise, never people."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ww.Store(os.path.join(self.tmp.name, "i.sqlite"))
        self.args = type("A", (), {"vision": "x", "model": "m", "recap_timeout": 1})()
        self.real = ww.ask_text
        self.calls = []
        ww._recap_cache.clear()
        self.day = "2026-10-09"
        for t, name, place, rel in [("08:00:00", "keys", "desk", "left"),
                                    ("08:01:00", "keys", "desk", "left"),
                                    ("09:30:00", "wallet", "kitchen counter", ""),
                                    ("10:15:00", "keys", "hallway table", "beside the bowl"),
                                    ("10:16:00", "mug", "o&#x27;brien shelf", "")]:
            self.add(t, name, place, rel)
        self.add("23:59:00", "glasses", "sofa", "", day="2026-10-08")  # another day

    def tearDown(self):
        ww.ask_text = self.real
        self.tmp.cleanup()

    def add(self, t, name, place, rel, day=None):
        when = f"{day or self.day}T{t}"
        self.store.q("INSERT INTO photos(file,taken_at,place) VALUES(?,?,?)", (f"{when}-{name}.jpg", when, place))
        pid = self.store.q("SELECT MAX(id) FROM photos")[0][0]
        self.store.q("INSERT INTO sightings(photo_id,name,aliases,place,relative_position,confidence,seen_at)"
                     " VALUES(?,?,'[]',?,?,0.9,?)", (pid, name, place, rel, when))

    def model(self, answer):
        def fake(url, model, prompt, timeout):
            self.calls.append(prompt)
            if isinstance(answer, BaseException):
                raise answer
            return answer
        ww.ask_text = fake

    def test_empty_day_needs_no_model(self):
        self.model("should not be asked")
        r = ww.recap(self.store, self.args, "2026-01-01")
        self.assertEqual((r["source"], r["sightings"], self.calls), ("plain", 0, []))

    def test_model_summary_is_used_and_escaped(self):
        self.model("Your keys <b>moved</b> from the desk to the hallway table at 10:15.")
        r = ww.recap(self.store, self.args, self.day)
        self.assertEqual(r["source"], "model")
        self.assertNotIn("<", r["summary"])
        self.assertEqual((r["sightings"], r["things"], r["places"]), (5, 3, 4))

    def test_only_that_days_sightings_reach_the_model(self):
        self.model("Your keys were on the hallway table.")
        ww.recap(self.store, self.args, self.day)
        prompt = self.calls[0]
        self.assertNotIn("glasses", prompt)
        self.assertEqual(prompt.count("keys at desk"), 1)          # repeat collapsed
        self.assertIn("o'brien shelf", prompt)                     # stored escapes undone for the model
        self.assertIn("10:15 keys at hallway table (beside the bowl)", prompt)

    def test_a_person_in_the_answer_falls_back_to_plain(self):
        for bad in ["She left your keys on the desk.", "They moved the wallet.",
                    "Your keys were held at 10:15.", "Someone took the mug."]:
            ww._recap_cache.clear()
            self.model(bad)
            r = ww.recap(self.store, self.args, self.day)
            self.assertEqual(r["source"], "plain", bad)
            self.assertFalse(ww.PEOPLE.search(r["summary"]), bad)

    def test_model_failure_falls_back_to_plain_last_seen(self):
        self.model(TimeoutError("slow"))
        r = ww.recap(self.store, self.args, self.day)
        self.assertEqual(r["source"], "plain")
        self.assertIn("keys at hallway table (10:15)", r["summary"])
        self.assertNotIn("keys at desk", r["summary"])               # last place only
        self.assertIn("between 08:00 and 10:16", r["summary"])

    def test_where_things_are_now_never_comes_from_the_model(self):
        # Seen live on Qwen3-VL-8B (9 Oct): "The last place each thing was seen was the desk."
        self.model("Your keys moved to the hallway table. Everything ended up on the desk.")
        s = ww.recap(self.store, self.args, self.day)["summary"]
        self.assertTrue(s.startswith("Your keys moved"))
        self.assertTrue(s.endswith("Last seen: mug at o&#x27;brien shelf (10:16); keys at hallway table (10:15); "
                                   "wallet at kitchen counter (09:30)."), s)

    def test_last_seen_lists_the_newest_and_counts_the_rest(self):
        rows = [(f"t{i}", "desk", "", f"{self.day}T10:{i:02d}:00") for i in range(9)]
        line = ww.last_seen(rows)
        self.assertTrue(line.startswith("Last seen: t8 at desk (10:08)"))
        self.assertTrue(line.endswith("; and 3 more."))

    def test_thinking_and_empty_answers(self):
        self.model("<think>the user wants a recap</think> Your mug is on the shelf.")
        s = ww.recap(self.store, self.args, self.day)["summary"]
        self.assertTrue(s.startswith("Your mug is on the shelf. Last seen:"), s)
        ww._recap_cache.clear()
        self.model("   ")
        self.assertEqual(ww.recap(self.store, self.args, self.day)["source"], "plain")

    def test_cached_until_the_day_changes(self):
        self.model("Your keys were on the hallway table.")
        ww.recap(self.store, self.args, self.day)
        ww.recap(self.store, self.args, self.day)
        self.assertEqual(len(self.calls), 1)                        # same index, no second call
        self.add("11:00:00", "charger", "desk", "")
        ww.recap(self.store, self.args, self.day)
        self.assertEqual(len(self.calls), 2)                        # new sighting, new recap

    def test_a_failure_is_retried_later_not_cached_forever(self):
        self.model(TimeoutError("slow"))
        ww.recap(self.store, self.args, self.day)
        ww.recap(self.store, self.args, self.day)
        self.assertEqual(len(self.calls), 1)                        # not hammered while down
        real_time = ww.time.time
        ww.time.time = lambda: real_time() + ww.RECAP_FAIL_SECONDS + 1
        try:
            ww.recap(self.store, self.args, self.day)
        finally:
            ww.time.time = real_time
        self.assertEqual(len(self.calls), 2)

    def test_long_days_keep_the_newest_lines(self):
        rows = [(f"thing{i}", f"place{i}", "", f"{self.day}T{i // 60:02d}:{i % 60:02d}:00")
                for i in range(ww.RECAP_LINES + 30)]
        text = ww.digest(rows)
        self.assertTrue(text.startswith("(plus 30 earlier sightings)"))
        self.assertIn(f"thing{ww.RECAP_LINES + 29} ", text)
        self.assertNotIn("thing0 ", text)


class Clean(unittest.TestCase):
    def test_markup_cannot_reach_the_page(self):
        self.assertNotIn("<", ww.clean("<img src=x onerror=alert(1)>"))

    def test_length_is_capped(self):
        self.assertEqual(len(ww.clean("x" * 500, 40)), 40)


if __name__ == "__main__":
    unittest.main()

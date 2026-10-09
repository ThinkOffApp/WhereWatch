"""Unit tests for the parts of wherewatch_base.py that need no model or server.

Run: python3 -m unittest base/test_base.py
"""
import json
import os
import sys
import time
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
    """The day recap: model-told when every word checks out, plain otherwise."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ww.Store(os.path.join(self.tmp.name, "i.sqlite"))
        self.args = type("A", (), {"vision": "x", "model": "m", "recap_timeout": 1})()
        self.real = ww.ask_text
        self.calls = []
        for d in (ww._recap_cache, ww._recap_backoff, ww._recap_inflight):
            d.clear()
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

    def model(self, answer, delay=0):
        def fake(url, model, prompt, timeout):
            self.calls.append(prompt)
            if delay:
                time.sleep(delay)
            if isinstance(answer, BaseException):
                raise answer
            return answer
        ww.ask_text = fake

    def recap(self, day=None):
        return ww.recap(self.store, self.args, day or self.day)

    def fresh(self):
        for d in (ww._recap_cache, ww._recap_backoff):
            d.clear()

    def test_empty_day_needs_no_model(self):
        self.model("should not be asked")
        r = self.recap("2026-01-01")
        self.assertEqual((r["source"], r["sightings"], self.calls), ("plain", 0, []))

    def test_model_story_is_used_escaped_and_counted(self):
        self.model("Your keys moved <from the desk> to the hallway table at 10:15.")
        r = self.recap()
        self.assertEqual(r["source"], "model")
        self.assertNotIn("<", r["summary"])
        self.assertEqual((r["sightings"], r["things"], r["places"]), (5, 3, 4))

    def test_answers_seen_from_the_real_model_pass_the_word_check(self):
        # Qwen3-VL-8B on one DGX Spark, 9 Oct, for a seeded day (names/places as in the seed)
        rows = [("keys", "hallway table", "beside the bowl", f"{self.day}T07:52:00"),
                ("glasses case", "kitchen table", "beside the coffee machine", f"{self.day}T08:10:00"),
                ("wallet", "desk", "under the monitor", f"{self.day}T09:40:00"),
                ("headphones", "sofa", "left armrest", f"{self.day}T12:05:00"),
                ("keys", "desk", "next to the laptop", f"{self.day}T13:30:00"),
                ("charger", "desk", "plugged in by the lamp", f"{self.day}T14:02:00")]
        for text in ["Your keys were on the hallway table at 07:52 and later moved to the desk at 13:30. "
                     "Your wallet was on the desk at 09:40. Your headphones were on the sofa at 12:05. "
                     "Your charger was at the desk at 14:02.",
                     "Your glasses case was at the kitchen table beside the coffee machine at 08:10. "
                     "Your headphones were at the sofa's left armrest at 12:05."]:
            self.assertTrue(ww.model_text_ok(text, rows), text)

    def test_only_that_days_sightings_reach_the_model(self):
        self.model("Your keys were on the hallway table.")
        self.recap()
        prompt = self.calls[0]
        self.assertNotIn("glasses", prompt)
        self.assertEqual(prompt.count("keys at desk"), 1)          # repeat collapsed
        self.assertIn("o'brien shelf", prompt)                     # stored escapes undone for the model
        self.assertIn("10:15 keys at hallway table (beside the bowl)", prompt)

    def test_photos_with_several_things_still_collapse_per_thing(self):
        rows = []
        for minute in range(3):  # one still a minute of a desk with keys and wallet
            for name in ("keys", "wallet"):
                rows.append((name, "desk", "", f"{self.day}T09:{minute:02d}:00"))
        self.assertEqual(ww.digest(rows).count("\n") + 1, 2)

    def test_people_names_and_other_languages_fall_back_to_plain(self):
        for bad in ["She left your keys on the desk.", "They moved the wallet.",
                    "Your keys were held at 10:15.", "Someone took the mug.",
                    "Anna moved your keys to the hallway table at 10:15.",
                    "Your wife put the wallet on the kitchen counter at 09:30.",
                    "Your keys were moved to the hallway table by the guest herself.",
                    "Hän siirsi avaimet eteisen pöydälle klo 10.15.",
                    "Your keys went to the hallway table, probably for the dog walk."]:
            self.fresh()
            self.model(bad)
            r = self.recap()
            self.assertEqual(r["source"], "plain", bad)
            for word in ("She", "They", "held", "Someone", "Anna", "wife", "herself", "Hän", "dog"):
                self.assertNotIn(word, r["summary"], bad)

    def test_model_failure_falls_back_to_plain_last_seen(self):
        self.model(TimeoutError("slow"))
        r = self.recap()
        self.assertEqual(r["source"], "plain")
        self.assertIn("keys at hallway table (10:15)", r["summary"])
        self.assertNotIn("keys at desk", r["summary"])               # last place only
        self.assertIn("between 08:00 and 10:16", r["summary"])

    def test_where_things_are_now_never_comes_from_the_model(self):
        # Seen live on Qwen3-VL-8B (9 Oct): "The last place each thing was seen was the desk."
        self.model("Your keys moved to the hallway table, then all ended up on the desk.")
        s = self.recap()["summary"]
        self.assertTrue(s.startswith("Your keys moved"), s)
        self.assertTrue(s.endswith("Last seen: mug at o&#x27;brien shelf (10:16); keys at hallway table (10:15); "
                                   "wallet at kitchen counter (09:30)."), s)

    def test_last_seen_lists_the_newest_and_counts_the_rest(self):
        rows = [(f"t{i}", "desk", "", f"{self.day}T10:{i:02d}:00") for i in range(9)]
        line = ww.last_seen(rows)
        self.assertTrue(line.startswith("Last seen: t8 at desk (10:08)"))
        self.assertTrue(line.endswith("; and 3 more."))

    def test_reasoning_never_reaches_the_card(self):
        self.model("<think>the user wants a recap</think> Your mug is on the shelf.")
        self.assertTrue(self.recap()["summary"].startswith("Your mug is on the shelf. Last seen:"))
        for leaky in ["Okay, the user wants a recap of keys.</think>Your mug is on the shelf.",  # template opened <think>
                      "<think>Okay, let me go through the sightings. At 08:00 the keys"]:          # cut off mid-thought
            self.fresh()
            self.model(leaky)
            r = self.recap()
            self.assertNotIn("think", r["summary"], leaky)
            self.assertNotIn("Okay", r["summary"], leaky)
        self.fresh()
        self.model("   ")
        self.assertEqual(self.recap()["source"], "plain")

    def test_cache_follows_this_days_rows_only(self):
        self.model("Your keys were on the hallway table.")
        self.recap()
        self.recap()
        self.assertEqual(len(self.calls), 1)                        # same rows, no second call
        self.add("09:00:00", "charger", "desk", "", day="2026-10-10")
        self.recap()
        self.assertEqual(len(self.calls), 1)                        # another day changed: still cached
        self.add("11:00:00", "charger", "desk", "")
        self.recap()
        self.assertEqual(len(self.calls), 2)                        # new sighting today: new recap
        self.store.q("DELETE FROM sightings WHERE name='wallet'")
        r = self.recap()
        self.assertEqual(len(self.calls), 3)                        # deleted sighting: new recap
        self.assertNotIn("wallet", r["summary"])

    def test_a_model_outage_backs_off_per_day_then_retries(self):
        self.model(TimeoutError("slow"))
        self.recap()
        self.recap()
        self.add("11:00:00", "charger", "desk", "")                  # a new sighting does not end the backoff
        self.recap()
        self.assertEqual(len(self.calls), 1)
        real_time = ww.time.time
        ww.time.time = lambda: real_time() + ww.RECAP_FAIL_SECONDS + 1
        try:
            self.recap()
        finally:
            ww.time.time = real_time
        self.assertEqual(len(self.calls), 2)

    def test_concurrent_requests_share_one_model_call(self):
        import threading
        self.model("Your keys were on the hallway table.", delay=0.2)
        out = []
        ts = [threading.Thread(target=lambda: out.append(self.recap())) for _ in range(5)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual({r["source"] for r in out}, {"model"})
        self.assertEqual(ww._recap_inflight, {})

    def test_long_days_keep_the_newest_lines(self):
        rows = [(f"thing{i}", f"place{i}", "", f"{self.day}T{i // 60:02d}:{i % 60:02d}:00")
                for i in range(ww.RECAP_LINES + 30)]
        text = ww.digest(rows)
        self.assertTrue(text.startswith("(plus 30 earlier changes)"))
        self.assertIn(f"thing{ww.RECAP_LINES + 29} ", text)
        self.assertNotIn("thing0 ", text)

    def test_the_endpoint_rejects_bad_days(self):
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer
        self.model("Your keys were on the hallway table.")
        srv = ThreadingHTTPServer(("127.0.0.1", 0), ww.make_handler(self.store, self.args))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}/api/recap"
        try:
            for bad in ["2026-02-30", "x", "../etc", "2026-1-1"]:
                with self.assertRaises(urllib.error.HTTPError) as e:
                    urllib.request.urlopen(f"{base}?day={bad}", timeout=5)
                self.assertEqual(e.exception.code, 400, bad)
                e.exception.close()
            with urllib.request.urlopen(f"{base}?day={self.day}", timeout=5) as r:
                self.assertEqual(json.load(r)["source"], "model")
        finally:
            srv.shutdown()
            srv.server_close()


class Clean(unittest.TestCase):
    def test_markup_cannot_reach_the_page(self):
        self.assertNotIn("<", ww.clean("<img src=x onerror=alert(1)>"))

    def test_length_is_capped(self):
        self.assertEqual(len(ww.clean("x" * 500, 40)), 40)


if __name__ == "__main__":
    unittest.main()

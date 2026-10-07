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
        (_, _, x2, y2), = ww.face_boxes({"faces": [[900, 900, 1000, 1000]]}, 100, 100)
        self.assertEqual((x2, y2), (100, 100))

    def test_people_without_usable_boxes_fails_closed(self):
        self.assertIsNone(ww.face_boxes({"people": True, "faces": []}, 10, 10))
        self.assertIsNone(ww.face_boxes({"people": True, "faces": [["x"], [1, 2]]}, 10, 10))
        self.assertEqual(ww.face_boxes({"people": False, "faces": []}, 10, 10), [])

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


class Clean(unittest.TestCase):
    def test_markup_cannot_reach_the_page(self):
        self.assertNotIn("<", ww.clean("<img src=x onerror=alert(1)>"))

    def test_length_is_capped(self):
        self.assertEqual(len(ww.clean("x" * 500, 40)), 40)


if __name__ == "__main__":
    unittest.main()

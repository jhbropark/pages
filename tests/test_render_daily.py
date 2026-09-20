"""The buffer's contract with the daily render."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(ROOT / "scripts"))
cards = _load("editorial_cards")
render_daily = _load("render_daily")


def buffered():
    path = ROOT / "content" / "buffer.json"
    items = json.loads(path.read_text(encoding="utf-8"))["items"]
    return [i for i in items if not i.get("consumed_at")]


class EveryBufferedItemRenders(unittest.TestCase):
    """Copy waiting to be posted must survive both formats it can land on."""

    def test_every_item_renders_as_a_single_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_daily.IMAGES_DIR = Path(tmp)
            for i, item in enumerate(buffered()):
                names = render_daily.render_post(item, f"single{i}", 1)
                self.assertEqual(len(names), 1, item["topic"])
                self.assertEqual(Image.open(Path(tmp) / names[0]).size, (1080, 1350))

    def test_items_with_slides_render_a_full_carousel(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_daily.IMAGES_DIR = Path(tmp)
            for i, item in enumerate(buffered()):
                if not item.get("slides"):
                    continue
                names = render_daily.render_post(item, f"deck{i}", 4)
                self.assertEqual(len(names), 4, item["topic"])
                for name in names:
                    self.assertEqual(Image.open(Path(tmp) / name).size, (1080, 1350))

    def test_an_item_without_slides_cannot_fill_a_carousel(self):
        """The gap the format downgrade exists for.

        An item carrying only a headline has nothing to build a deck from, so
        render_post returns one card. render_slot must not then queue it as a
        carousel — a one-image carousel is just a single image with a wrong
        label on it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            render_daily.IMAGES_DIR = Path(tmp)
            bare = {"image_headline": "헤드라인만 있는 항목", "topic": "t"}
            self.assertEqual(len(render_daily.render_post(bare, "bare", 4)), 1)


class Buffer(unittest.TestCase):
    def test_holds_whole_days(self):
        slots = len(json.loads(
            (ROOT / "content" / "topics.json").read_text(encoding="utf-8"))["daily_slots"])
        self.assertEqual(len(buffered()) % slots, 0,
                         "buffer should hold complete days, not half of one")

    def test_no_topic_is_queued_twice(self):
        topics = [i["topic"] for i in buffered()]
        self.assertEqual(len(topics), len(set(topics)))

    def test_every_item_names_a_resolvable_image(self):
        for item in buffered():
            for name in [item.get("image", "")] + \
                    [s.get("image", "") for s in item.get("slides", [])]:
                if name:
                    self.assertIsNotNone(cards.resolve_image(name), name)


if __name__ == "__main__":
    unittest.main()

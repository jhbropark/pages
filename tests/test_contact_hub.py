import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ContactHubTests(unittest.TestCase):
    def test_contact_hub_has_multiple_contact_paths(self):
        html = (ROOT / "contact.html").read_text(encoding="utf-8")
        self.assertIn("https://ig.me/m/bbbb.beauty_official", html)
        self.assertIn("https://www.linkedin.com/in/im-jay-974408415/", html)
        self.assertIn('id="copy"', html)
        self.assertIn('id="brief"', html)

    def test_strategy_points_to_contact_hub(self):
        strategy = json.loads(
            (ROOT / "content" / "strategy.json").read_text(encoding="utf-8")
        )
        contact = strategy["conversion_system"]["contact"]
        self.assertEqual(
            contact["website_url"],
            "https://jhbropark.github.io/pages/contact.html",
        )


if __name__ == "__main__":
    unittest.main()

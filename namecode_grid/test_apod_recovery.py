"""Offline outage regressions; no Krea/publication calls."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from test_apod_namecode import apod

HTML = '''<h1>Chasing the International Space Station</h1>
<p><strong>Explanation:</strong>Blasting into the predawn sky, a rocket and Dragon spacecraft are headed for low Earth orbit in a stunning video. Complete scientific explanation continues here.<br><br><strong>Tomorrow's picture:</strong>space</p>
<table><tr><th>Date</th><td>October 16, 2026</td></tr><tr><th>Video Credit:</th><td>Eric Holland</td></tr></table>'''

class Recovery(unittest.TestCase):
    def test_api500_falls_back_to_dated_html(self):
        response = Mock(text=HTML)
        with patch.object(apod.requests, 'get', side_effect=[apod.requests.RequestException('500'), response]), patch.object(apod.time, 'sleep'):
            data = apod.get_apod('2026-10-16', retries=1)
        self.assertEqual(data['title'], 'Chasing the International Space Station')
        self.assertEqual(data['copyright'], 'Eric Holland')
        self.assertEqual(data['media_type'], 'video')

    def test_corrupt_api200_uses_html(self):
        bad = Mock()
        bad.json.return_value = dict(date='2026-10-16', title='NASA Science', explanation='cut')
        good = Mock(text=HTML)
        with patch.object(apod.requests, 'get', side_effect=[bad, good]) as get:
            result = apod.get_apod('2026-10-16')
        self.assertEqual(result['title'], 'Chasing the International Space Station')
        self.assertIn('?date=261016', get.call_args.args[0])

    def test_truncated_api200_uses_html(self):
        bad = Mock()
        bad.json.return_value = dict(date='2026-10-16', title='Real title', explanation='cut')
        with patch.object(apod.requests, 'get', side_effect=[bad, Mock(text=HTML)]):
            self.assertEqual(apod.get_apod('2026-10-16')['copyright'], 'Eric Holland')

    def test_future_day_is_rejected_before_network(self):
        with patch.object(apod.requests, 'get') as get:
            with self.assertRaises(ValueError):
                apod.get_apod('2099-01-01')
            get.assert_not_called()



    def test_2026_10_20_api_error_uses_updated_article_parser(self):
        fixture = Path(__file__).parent / "fixtures" / "apod_2026-10-20.html"
        with patch.object(apod.requests, 'get', side_effect=[
            apod.requests.HTTPError('500'),
            Mock(text=fixture.read_text(encoding="utf-8")),
        ]), patch.object(apod.time, 'sleep'):
            result = apod.get_apod('2026-10-20', retries=1)
        self.assertEqual(result['date'], '2026-10-20')
        self.assertEqual(result['title'], "An Anticrepuscular Rainbow Fan")
        self.assertGreaterEqual(len(result['explanation']), 80)

    def test_2026_10_20_nasa_article_fixture_plain_explanation_label(self):
        fixture = Path(__file__).parent / "fixtures" / "apod_2026-10-20.html"
        html = fixture.read_text(encoding="utf-8")
        result = apod.parse_apod_html(html, "2026-10-20")
        self.assertEqual(result["title"], "An Anticrepuscular Rainbow Fan")
        self.assertGreaterEqual(len(result["explanation"]), 80)
        self.assertIn("sunlit fan", result["explanation"])

    def test_official_article_fixture_still_rejects_wrong_date(self):
        fixture = Path(__file__).parent / "fixtures" / "apod_2026-10-20.html"
        html = fixture.read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "date mismatch"):
            apod.parse_apod_html(html, "2026-10-21")

    def test_wrong_day_is_rejected(self):
        with self.assertRaises(ValueError):
            apod.parse_apod_html(HTML, '2026-10-17')

    def test_invalid_day_is_rejected(self):
        with self.assertRaises(ValueError):
            apod.get_apod('2026-02-30')


    def test_three_api_500s_fall_back_to_date_verified_html(self):
        with patch.object(apod.requests, 'get', side_effect=[
            apod.requests.HTTPError('500'),
            apod.requests.HTTPError('500'),
            apod.requests.HTTPError('500'),
            Mock(text=HTML),
        ]), patch.object(apod.time, 'sleep'):
            result = apod.get_apod('2026-10-16', retries=3)
        self.assertEqual(result['date'], '2026-10-16')
        self.assertEqual(result['title'], 'Chasing the International Space Station')

    def test_timeout_and_html_404s_fail_closed_after_retries(self):
        with patch.object(apod.requests, 'get', side_effect=[
            apod.requests.Timeout('timed out'),
            apod.requests.HTTPError('404'),
            apod.requests.HTTPError('404'),
            apod.requests.HTTPError('404'),
            apod.requests.HTTPError('404'),
        ]), patch.object(apod.time, 'sleep'):
            with self.assertRaises(apod.requests.RequestException):
                apod.get_apod('2026-10-16', retries=1)

    def test_curated_captions_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            out = str(Path(d) / 'caption.txt')
            curated = apod.caption_variant_path(out, '_reel_instagram')
            Path(curated).write_text('Human curated', encoding='utf-8')
            apod.write_captions({'date':'2026-10-16', 'work_name':'TEST', 'apod_title':'Test', 'label':'test'}, out)
            self.assertEqual(Path(curated).read_text(encoding='utf-8'), 'Human curated')

    def test_workflow_checks_existing_assets_before_generator(self):
        text = (Path(__file__).parent.parent / '.github/workflows/namecode-daily.yml').read_text(encoding='utf-8')
        self.assertLess(text.index('compgen -G'), text.index('python apod_namecode.py'))
        self.assertIn("steps.gen.outputs.fresh == 'true'", text)

if __name__ == '__main__':
    unittest.main()

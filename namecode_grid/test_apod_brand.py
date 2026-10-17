"""Offline subject/brand-review regressions; no generated images or network."""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from test_apod_namecode import apod
from test_apod_recovery import HTML


class BrandPrompt(unittest.TestCase):
    def test_named_subject_precedes_context_and_style(self):
        text = apod.build_prompt('Lunar Farside', 'The far side is covered in craters.')
        self.assertTrue(text.startswith('Visual subject: Lunar Farside.\n'))
        self.assertLess(text.index('Scene context'), text.index('Style:'))
        self.assertIn('The far side is covered in craters.', text)

    def test_source_context_does_not_end_at_old_200_character_cut(self):
        first = 'A crater ' + 'with visible ridges ' * 12 + 'fills the frame.'
        explanation = first + ' A second complete sentence explains the surface.'
        context = apod.visual_context(explanation)
        self.assertIn(first, context)
        self.assertGreater(len(context), 200)
        self.assertTrue(context.endswith('.'))

    def test_long_context_uses_whole_sentences_without_changing_them(self):
        sentence = 'Bright filaments outline the nebula in the dark sky.'
        text = ' '.join([sentence] * 40)
        context = apod.visual_context(text)
        self.assertEqual(context, ' '.join([sentence] * 3))
        self.assertLessEqual(len(context), 800)

    def test_an_overlong_unfinished_fragment_is_omitted(self):
        self.assertEqual(apod.visual_context('unfinished fragment ' * 100), '')

    def test_generic_titles_are_refused(self):
        for title in ('NASA Science', 'NASA.SCIENCE', ' nasa science ',
                      'APOD', 'Astronomy Picture of the Day', ''):
            with self.subTest(title=title), self.assertRaises(ValueError):
                apod.build_prompt(title, 'A real scene.')

    def test_specific_non_latin_manual_subject_is_not_generic(self):
        self.assertTrue(apod.build_prompt('달의 뒷면').startswith('Visual subject: 달의 뒷면.'))

    def test_player_placeholder_is_not_scene_context(self):
        with self.assertRaises(ValueError):
            apod.build_prompt('Chasing the International Space Station',
                              'To view this video please enable JavaScript, ' * 5)

    def test_player_placeholder_api200_uses_html(self):
        bad = Mock()
        bad.json.return_value = dict(date='2026-10-16', title='Chasing the International Space Station',
                                    explanation='To view this video please enable JavaScript, ' * 5)
        with patch.object(apod.requests, 'get', side_effect=[bad, Mock(text=HTML)]):
            data = apod.get_apod('2026-10-16')
        self.assertEqual(data['copyright'], 'Eric Holland')
        self.assertNotIn('JavaScript', data['explanation'])

    def test_generic_punctuation_api200_uses_html(self):
        bad = Mock()
        bad.json.return_value = dict(date='2026-10-16', title='NASA.SCIENCE',
                                    explanation='A bogus page description. ' * 8)
        with patch.object(apod.requests, 'get', side_effect=[bad, Mock(text=HTML)]):
            self.assertEqual(apod.get_apod('2026-10-16')['title'],
                             'Chasing the International Space Station')

    def test_existing_monochrome_style_is_kept(self):
        text = apod.build_prompt('Stickney Crater', 'A crater on Phobos.')
        for phrase in ('fine white particles', 'light filaments', 'pure black',
                       'monochrome white on black', 'negative space', 'high detail'):
            self.assertIn(phrase, text)
        self.assertIn('AI interpretation of text', text)
        self.assertNotIn('source photograph as reference', text)

    def test_brief_lists_review_targets_but_never_claims_visual_match(self):
        brief = apod.build_brief('2026-10-09', 'Stickney Crater', 'CRATER', '9 km',
                                'prompt', explanation='A crater on Phobos.')
        self.assertEqual(brief['visual_subject'], 'Stickney Crater')
        self.assertEqual(brief['visual_context'], 'A crater on Phobos.')
        self.assertTrue(brief['visual_review']['required'])
        self.assertEqual(brief['visual_review']['status'], 'pending')

    def test_manual_dryrun_has_review_metadata_without_paid_generation(self):
        out = io.StringIO()
        with patch.object(sys, 'argv', ['apod_namecode.py', '--subject', 'Lunar Farside',
                                       '--date', '2099-01-01', '--dry-run']), \
                patch.object(apod, 'load_dotenv'), patch.object(apod, 'krea_generate') as paid, \
                patch.object(apod.requests, 'get') as network, contextlib.redirect_stdout(out):
            apod.main()
        brief = json.loads(out.getvalue())
        paid.assert_not_called()
        network.assert_not_called()
        self.assertEqual(brief['visual_subject'], 'Lunar Farside')
        self.assertEqual(brief['visual_review']['status'], 'pending')

    def test_scheduled_stills_cannot_bypass_explicit_brand_review_approval(self):
        text = (Path(__file__).parent.parent / '.github/workflows/namecode-daily.yml').read_text(encoding='utf-8')
        for channel in ('Instagram', 'Facebook'):
            start = text.index(f'- name: Publish feed image to {channel} (optional)')
            block = text[start:text.index('working-directory:', start)]
            self.assertIn("github.event.inputs.publish == 'true'", block)
            self.assertNotIn("github.event_name == 'schedule'", block)
            self.assertIn("steps.gen.outputs.fresh == 'true'", block)
        self.assertIn('Explicit manual IG/FB publish approval after brand review', text)


if __name__ == '__main__':
    unittest.main()

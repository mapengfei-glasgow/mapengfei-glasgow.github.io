"""Offline regression checks: python3 -m unittest discover -s tools -p test_word_notes.py"""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import build_word_notes as notes


class WordNotesTests(unittest.TestCase):
    def test_markers_ignore_frontmatter_and_code(self):
        text = '---\ntitle: "[[Ignore]]"\n---\nThe [[Ottoman Empire]] fell.\n\n```text\n[[skip]]\n```\n\nUse `[[code]]` and [[aspiring]].'
        self.assertEqual(set(notes.marked_terms(text)), {'Ottoman Empire', 'aspiring'})

    def test_markers_read_from_episode_sentences(self):
        # Episode pages have no body: the transcript lives in front matter as
        # one-line flow mappings, which is where [[terms]] have to be found.
        text = (
            '---\n'
            'title: "A [[title]] title"\n'
            'sentences:\n'
            '  - {text: "The [[curfew]] began at dusk.", start: 0.0, end: 2.5, zh: "宵禁开始了。"}\n'
            '  - {text: "He said \\"stop\\" and left.", start: 3.0, end: 4.0}\n'
            '---\n'
        )
        terms = notes.marked_terms(text)
        self.assertEqual(set(terms), {'curfew'})
        # The context is the sentence with the markers removed, and the escaped
        # quote in the neighbouring sentence must not swallow the match.
        self.assertEqual(terms['curfew'], 'The curfew began at dusk.')

    def test_episode_sentences_and_body_together(self):
        text = (
            '---\n'
            'sentences:\n'
            '  - {text: "A [[curfew]] applies.", start: 0.0, end: 1.0}\n'
            '---\n'
            'Body prose with [[aspiring]].'
        )
        self.assertEqual(set(notes.marked_terms(text)), {'curfew', 'aspiring'})

    def test_cache_context_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'content').mkdir()
            (root / 'data').mkdir()
            article = root / 'content/article.md'
            article.write_text('An [[aspiring]] writer.')
            reply = {'choices': [{'message': {'content': json.dumps({'pronunciation': '', 'part_of_speech': 'adjective', 'meaning': '有抱负的', 'explanation': 'Hoping to become something.'})}}]}
            def response(*args, **kwargs):
                return io.BytesIO(json.dumps(reply).encode())
            with patch.object(notes, 'ROOT', root), patch('sys.argv', ['build_word_notes.py']), patch('urllib.request.urlopen', side_effect=response) as request:
                self.assertEqual(notes.main(), 0)
                self.assertEqual(notes.main(), 0)
                self.assertEqual(request.call_count, 1)
                article.write_text('An [[aspiring]] artist.')
                self.assertEqual(notes.main(), 0)
                self.assertEqual(request.call_count, 2)
                cache = (root / 'data/word_notes.json').read_text()
                article.write_text('An [[aspiring]] musician.')
                request.side_effect = OSError('offline')
                self.assertEqual(notes.main(), 1)
                self.assertEqual((root / 'data/word_notes.json').read_text(), cache)

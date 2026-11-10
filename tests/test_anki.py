# run: python tests/test_anki.py  (or pytest)
import time

import meikipop.anki as anki
from meikipop.anki import format_meaning, format_meanings, context_html, known_word_query, AnkiKnownWords
from meikipop.dictionary.lookup import DictionaryEntry
from meikipop.gui.input import to_pynput_hotkey


def test_hotkey_conversion():
    assert to_pynput_hotkey('alt+a') == '<alt>+a'
    assert to_pynput_hotkey('Ctrl + Shift + E') == '<ctrl>+<shift>+e'
    assert to_pynput_hotkey('f8') == '<f8>'


def test_format_meaning():
    entry = DictionaryEntry(id=1, written_form='食べる', reading='たべる', freq=100, deconjugation_process=(),
                            senses=[{'glosses': ['to eat'], 'pos': ['v1']},
                                    {'glosses': [], 'pos': []},
                                    {'glosses': ['to live on', 'to subsist on'], 'pos': []}])
    assert format_meaning(entry, all_meanings=False) == 'to eat; to live on'
    assert format_meaning(entry, all_meanings=True) == \
        '<ol><li><i>(v1)</i> to eat</li><li>to live on, to subsist on</li></ol>'


def test_format_meanings_combines_readings():
    corner = DictionaryEntry(1, '角', 'かど', [{'glosses': ['corner'], 'pos': []}], 1, ())
    horn = DictionaryEntry(2, '角', 'つの', [{'glosses': ['horn'], 'pos': []}], 1, ())
    assert format_meanings([corner], all_meanings=False) == 'corner'
    assert format_meanings([corner, horn], all_meanings=False) == '<div>【かど】 corner</div><div>【つの】 horn</div>'


def test_context_html():
    text = '「雨だ。」昨日、ケーキを食べた<友達>がいた。'
    # cursor on 食 (index 12), the dictionary matched 3 characters (食べた, conjugated)
    assert context_html(text, 12, 3) == '昨日、ケーキを<b>食べた</b>&lt;友達&gt;がいた。'
    assert context_html(text, 1, 1) == '「<b>雨</b>だ。'


def test_known_word_query():
    assert known_word_query('食べる', ['Expression', 'Word']) == '"Expression:食べる" OR "Word:食べる"'
    assert known_word_query('a*b"_', ['Word']) == '"Word:a\\*b\\"\\_"'


def _wait_for(condition, seconds=3.0):
    deadline = time.time() + seconds
    while not condition() and time.time() < deadline:
        time.sleep(0.01)


def test_known_words_checks_in_background():
    def fake_anki(action, **params):
        if action == 'modelNames':
            return ['Lapis', 'Basic']
        if action == 'modelFieldNames':
            return {'Lapis': ['Expression', 'Sentence'], 'Basic': ['Front', 'Back']}[params['modelName']]
        if action == 'findNotes':
            assert '"Expression:' in params['query'] and '"Word:' in params['query']
            return [42] if '食べる' in params['query'] else []

    real, anki.anki_request = anki.anki_request, fake_anki
    try:
        kw = AnkiKnownWords()
        assert kw.status(['食べる', '飲む']) == {}  # nothing known yet, checks start in the background
        _wait_for(lambda: kw.version >= 2)
        assert kw.status(['食べる', '飲む']) == {'食べる': True, '飲む': False}
        kw.mark_known('飲む')  # e.g. right after adding a card
        assert kw.status(['飲む']) == {'飲む': True}

        # anki closed: no answers, and no new attempts until the retry delay has passed
        def offline(action, **params):
            raise anki.requests.ConnectionError()
        anki.anki_request = offline
        kw2 = AnkiKnownWords()
        assert kw2.status(['猫']) == {}
        _wait_for(lambda: kw2._worker is None)
        assert kw2.status(['猫']) == {} and kw2._worker is None and not kw2._pending
    finally:
        anki.anki_request = real


if __name__ == '__main__':
    test_hotkey_conversion()
    test_format_meaning()
    test_format_meanings_combines_readings()
    test_context_html()
    test_known_word_query()
    test_known_words_checks_in_background()
    print('ok')

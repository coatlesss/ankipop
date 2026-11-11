# run: python tests/test_translate.py  (or pytest)
from meikipop.translate import sentence_at


def test_sentence_at():
    text = '「雨だ。」「傘はある？」ないよ'
    assert sentence_at(text, 1) == '「雨だ。'      # cursor on 雨
    assert sentence_at(text, 3) == '「雨だ。'      # cursor on the 。 itself
    assert sentence_at(text, 7) == '「傘はある？'  # leftover 」 from the previous sentence is dropped
    assert sentence_at(text, 14) == 'ないよ'       # last sentence without an ending mark
    assert sentence_at('こんにちは', 2) == 'こんにちは'


def test_popup_placed_beside_text():
    from PyQt6.QtCore import QRect, QSize
    from meikipop.gui.popup import Popup

    screen, size = QRect(0, 0, 1920, 1080), QSize(400, 80)
    place = lambda block, x, y, vertical=False: Popup._position_beside_text(x, y, block, vertical, size, screen)

    # (left, right, top, bottom) text blocks
    # VN text box at the bottom: no room below, so the popup goes above it
    _, y = place((600, 1300, 900, 1000), 960, 950)
    assert y + size.height() <= 900
    # subtitle at the top: popup goes below it
    _, y = place((600, 1300, 50, 150), 960, 100)
    assert y >= 150
    # manga column mid-screen: popup goes to its right (the side already read)
    x, _ = place((900, 1000, 100, 700), 950, 400, vertical=True)
    assert x >= 1000
    # manga column at the right screen edge: no room on the right, so it goes left
    x, _ = place((1450, 1550, 100, 700), 1500, 400, vertical=True)
    assert x + size.width() <= 1450


def test_rate_limit_shows_a_short_message_and_repeats_are_cached():
    from unittest.mock import MagicMock, patch
    import requests
    from meikipop import translate as t

    popup = MagicMock()
    popup.get_latest_data.side_effect = lambda: popup.set_latest_data.call_args[0][0]
    translator = t.SentenceTranslator.__new__(t.SentenceTranslator)  # skip the global hotkey listener
    translator.popup_window, translator.lookup = popup, None

    blocked = requests.Response()
    blocked.status_code = 429
    with patch.object(t.requests, 'get', return_value=blocked):
        translator._translate_into_popup('雨だ。')
    assert popup.set_latest_data.call_args[0][0][0].translation == t.RATE_LIMITED

    ok = MagicMock()
    ok.json.return_value = [[['It is raining.', '雨だ。']]]
    with patch.object(t.requests, 'get', return_value=ok) as get:
        assert t.translate('雨だ。') == 'It is raining.'
        assert t.translate('雨だ。') == 'It is raining.'
    assert get.call_count == 1  # the second press used the cache


def test_grammar_hotkey_shows_only_grammar():
    from unittest.mock import MagicMock, patch
    from meikipop import translate as t
    from meikipop.grammar_points import TEIRU

    popup = MagicMock()
    translator = t.SentenceTranslator.__new__(t.SentenceTranslator)  # skip the global hotkey listener
    translator.popup_window, translator.lookup = popup, None
    shown = lambda: popup.set_latest_data.call_args[0][0][0]

    with patch.object(t, 'find_grammar', return_value=[TEIRU]), patch.object(t.requests, 'get') as get:
        translator._grammar_into_popup('見てる。')
    assert shown().translation == '' and shown().grammar == (TEIRU,)
    assert not get.called  # no translation request

    with patch.object(t, 'find_grammar', return_value=[]):
        translator._grammar_into_popup('はい。')
    assert shown().translation == t.NO_GRAMMAR


def test_both_hotkeys_are_registered_unless_they_clash():
    from unittest.mock import MagicMock, patch
    from meikipop import translate as t

    translator = t.SentenceTranslator.__new__(t.SentenceTranslator)
    translator.listener = None
    with patch.object(t.config, 'translate_hotkey', 'alt+t'), patch.object(t.config, 'grammar_hotkey', 'alt+g'), \
            patch.object(t.keyboard, 'GlobalHotKeys') as hotkeys:
        translator.reapply_settings()
    assert set(hotkeys.call_args[0][0]) == {'<alt>+t', '<alt>+g'}
    with patch.object(t.config, 'translate_hotkey', 'alt+t'), patch.object(t.config, 'grammar_hotkey', 'alt+t'), \
            patch.object(t.keyboard, 'GlobalHotKeys') as hotkeys:
        translator.listener = None
        translator.reapply_settings()
    assert set(hotkeys.call_args[0][0]) == {'<alt>+t'}  # same key twice: translation wins


if __name__ == '__main__':
    test_sentence_at()
    test_popup_placed_beside_text()
    test_rate_limit_shows_a_short_message_and_repeats_are_cached()
    test_grammar_hotkey_shows_only_grammar()
    test_both_hotkeys_are_registered_unless_they_clash()
    print('ok')

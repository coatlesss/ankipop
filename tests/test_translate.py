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


if __name__ == '__main__':
    test_sentence_at()
    test_popup_placed_beside_text()
    print('ok')

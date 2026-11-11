# run: python tests/test_postprocessing.py  (or pytest)
from contextlib import contextmanager

from meikipop.config.config import config
from meikipop.ocr.interface import BoundingBox, Paragraph, Word
from meikipop.ocr.providers.postprocessing import group_lines_into_paragraphs


@contextmanager
def text_mode(mode):
    old, config.text_mode = config.text_mode, mode
    try:
        yield
    finally:
        config.text_mode = old


def _column(text, x, width=24):
    words = [Word(ch, '', BoundingBox(x, 167 + 25 * i, 20, 20)) for i, ch in enumerate(text)]
    return Paragraph(text, words, BoundingBox(x, 167 + 12.5 * (len(text) - 1), width, 25 * len(text)), True)


def _row(chars_at_x, y, size=15):
    words = [Word(ch, '', BoundingBox(x, y, size, size)) for ch, x in chars_at_x]
    xs = [x for _, x in chars_at_x]
    text = ''.join(ch for ch, _ in chars_at_x)
    return Paragraph(text, words, BoundingBox((min(xs) + max(xs)) / 2, y, max(xs) - min(xs) + size, size), False)


# the manga bubble from a real Screen AI scan: five columns, furigana beside 判断, and sideways rows through the columns
BUBBLE = [_column('それで', 264), _column('使える', 229), _column('モンか', 196), _column('どうか', 168),
          _column('はんだん', 147, width=17), _column('判断する', 126),
          _row([('断', 128), ('う', 166), ('ン', 196), ('え', 228), ('れ', 264)], y=192),
          _row([('モ', 196), ('使', 229), ('そ', 264)], y=167)]


def _texts(lines):
    return sorted(p.full_text for p in group_lines_into_paragraphs(list(lines)))


def test_manga_mode_reads_the_bubble():
    with text_mode('manga'):
        texts = _texts(BUBBLE)
    assert 'それで使えるモンかどうか判断する' in texts, texts  # furigana and sideways rows stay out of the sentence
    assert 'モ使そ' not in texts and '断うンえれ' not in texts, texts


def test_normal_mode_is_unchanged():
    with text_mode('normal'):
        texts = _texts(BUBBLE)
    assert any('モ使そ' in t for t in texts), texts  # normal mode keeps every line, as before manga mode existed


def test_manga_mode_keeps_real_horizontal_text():
    caption = _row([(ch, 20 + 15 * i) for i, ch in enumerate('ひとこと')], y=20)
    with text_mode('manga'):
        assert _texts([_column('それで', 264), caption]) == ['それで', 'ひとこと']


if __name__ == '__main__':
    test_manga_mode_reads_the_bubble()
    test_normal_mode_is_unchanged()
    test_manga_mode_keeps_real_horizontal_text()
    print('ok')

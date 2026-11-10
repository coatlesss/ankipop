# run: python tests/test_furigana.py  (or pytest)
from meikipop.anki import context_html
from meikipop.dictionary.furigana import kanji_readings, furigana_html
from meikipop.dictionary.lookup import DictionaryEntry

# a tiny stand-in dictionary: surface prefix -> (written form, reading, matched length)
WORDS = {'昨日': ('昨日', 'きのう', 2), 'ケーキ': ('ケーキ', '', 3), '食べた': ('食べる', 'たべる', 3),
         '友達': ('友達', 'ともだち', 2), 'ご飯': ('ご飯', 'ごはん', 2), '雨': ('雨', 'あめ', 1)}


class FakeLookup:
    def _do_lookup(self, text):
        for surface in sorted(WORDS, key=len, reverse=True):
            if text.startswith(surface):
                written, reading, n = WORDS[surface]
                return [DictionaryEntry(1, written, reading, [], 1, (), match_len=n)]
        return []


def test_kanji_readings():
    assert kanji_readings('食べる', 'たべる') == ['た']
    assert kanji_readings('引き出し', 'ひきだし') == ['ひ', 'だ']
    assert kanji_readings('今日', 'きょう') == ['きょう']
    assert kanji_readings('ご飯', 'ごはん') == ['はん']
    assert kanji_readings('食べる', 'のむ') is None  # doesn't line up


def test_furigana_html():
    assert furigana_html('昨日ご飯を食べた', FakeLookup()) == \
        '<ruby>昨日<rt>きのう</rt></ruby>ご<ruby>飯<rt>はん</rt></ruby>を<ruby>食<rt>た</rt></ruby>べた'
    assert furigana_html('ケーキ<だ>', FakeLookup()) == 'ケーキ&lt;だ&gt;'  # no kanji: just escaped
    assert furigana_html('謎', FakeLookup()) == '謎'  # unknown kanji: left bare


def test_common_reading_beats_longer_expression():
    class Lookup:  # 今日は matches the greeting こんにちは (longer) and 今日 きょう (more common)
        def _do_lookup(self, text):
            if not text.startswith('今日'):
                return []
            return [DictionaryEntry(1, '今日は', 'こんにちは', [], 33000, (), priority=5.5, match_len=3),
                    DictionaryEntry(2, '今日', 'きょう', [], 97, (), priority=8.7, match_len=2),
                    DictionaryEntry(3, '今日', 'こんにち', [], 999999, (), priority=2.0, match_len=2)]
    assert furigana_html('今日は晴れ', Lookup()) == '<ruby>今日<rt>きょう</rt></ruby>は晴れ'


def test_context_keeps_target_word_bare():
    # cursor on 食 (index 5), word 食べた: bold and no furigana; the rest of the sentence gets readings
    assert context_html('昨日友達と食べた。', 5, 3, FakeLookup()) == \
        '<ruby>昨日<rt>きのう</rt></ruby><ruby>友達<rt>ともだち</rt></ruby>と<b>食べた</b>。'


if __name__ == '__main__':
    test_kanji_readings()
    test_furigana_html()
    test_common_reading_beats_longer_expression()
    test_context_keeps_target_word_bare()
    print('ok')

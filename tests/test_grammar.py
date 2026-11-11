# run: python tests/test_grammar.py  (or pytest)
import re
from types import SimpleNamespace

from meikipop.dictionary.deconjugator import Form
from meikipop.dictionary.lookup import DictionaryEntry
from meikipop.grammar import find_grammar
from meikipop.grammar_points import PHRASES

# a tiny stand-in dictionary: surface -> (dictionary form, deconjugation steps outermost first, as the deconjugator
# reports them). Plain words are their own dictionary form.
PLAIN = ['テレビ', 'を', 'けど', '新しい', '本', 'なら', 'ない', 'と', 'した', 'する', 'れる', 'ように', 'している', '食べる']
WORDS = {w: (w, ()) for w in PLAIN} | {
    '見てる': ('見る', ('teru (teiru)', '(te form)', '(unstressed infinitive)')),
    '行かなければ': ('行く', ('provisional conditional', '(ke stem)', 'negative', '(mizenkei)')),
    '開けよう': ('開ける', ('volitional',)),
    '書いたり': ('書く', ('tari', '(unstressed infinitive)')),
    '読んだり': ('読む', ('tari', '(unstressed infinitive)')),
    '教えてく': ('教える', ('teku (teiku)', '(te form)', '(unstressed infinitive)')),  # how the real dictionary splits 教えてくれる
    '食べさせられた': ('食べる', ('past', '(unstressed infinitive)', 'passive/potential', 'causative')),
}


class FakeDeconjugator:
    def deconjugate(self, surface):
        form, steps = WORDS.get(surface, (surface, ()))
        return {Form(form, steps)}


class FakeLookup:
    deconjugator = FakeDeconjugator()
    dictionary = SimpleNamespace(entries={})

    def _do_lookup(self, text):
        for surface in sorted(WORDS, key=len, reverse=True):
            if text.startswith(surface):
                form, steps = WORDS[surface]
                return [DictionaryEntry(1, form, '', [], 1, steps, match_len=len(surface))]
        return []


def names(sentence):
    return [p.name for p in find_grammar(sentence, FakeLookup())]


def test_every_phrase_matches_its_example():
    for phrase in PHRASES:
        assert re.search(phrase.pattern, phrase.example), f'{phrase.point.name}: {phrase.pattern} vs {phrase.example}'


def test_conjugations_and_phrases_in_sentence_order():
    assert names('テレビを見てるけど') == ['〜ている', '〜けど']
    assert names('食べさせられた') == ['causative 〜させる', '〜られる']  # innermost step first


def test_phrase_inside_a_word_is_ignored():
    assert names('新しい本') == []  # らしい inside 新しい


def test_phrase_hides_the_steps_it_explains():
    assert names('行かなければならない') == ['〜なければならない / 〜なきゃ']  # not also 〜ば
    assert names('開けようとした') == ['〜ようとする']  # not also volitional
    assert names('教えてくれる') == ['〜てくれる']  # not the dictionary's 教えてく (〜ていく)


def test_longer_phrase_wins_and_points_are_listed_once():
    assert names('食べるようにしている') == ['〜ようにする', '〜ている']  # not also 〜ように
    assert names('書いたり読んだりする') == ['〜たり〜たりする']


if __name__ == '__main__':
    test_every_phrase_matches_its_example()
    test_conjugations_and_phrases_in_sentence_order()
    test_phrase_inside_a_word_is_ignored()
    test_phrase_hides_the_steps_it_explains()
    test_longer_phrase_wins_and_points_are_listed_once()
    print('ok')

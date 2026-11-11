# meikipop/grammar.py
"""Finds the grammar points in a sentence, shown under its translation.

1. Conjugations: the sentence is split into words by longest dictionary match (the way the popup reads them). Each word
   is deconjugated again and the simplest valid reading is used, so 食べさせられた is always causative + passive and
   手伝って is just a te-form (not the stem of 手伝ってる). Its steps become grammar points through CONJUGATION_POINTS.
   A word that is also a dictionary word of its own (読める) still gets the grammar of its conjugated reading
   (読む + potential) when that reading's stem is in the text.
2. Phrases: fixed patterns (かもしれない, なければならない, ...) are matched with regexes. Phrases marked at_word_start
   only count where a word starts, so らしい in 新しい is ignored. Word starts come from the split that prefers common
   words (the furigana one), so particles like の and ので stand on their own.
"""
import re

from meikipop.dictionary.furigana import MAX_WORD_LEN, _best_entry
from meikipop.grammar_points import CONJUGATION_POINTS, PHRASES, GrammarPoint

_COMPILED = [(re.compile(phrase.pattern), phrase) for phrase in PHRASES]
_KANJI = re.compile(r'[一-鿿々]')
PARTICLES = 'はがをにでともへやのか'
CUT_OFF_STEMS = {'(ka stem)', '(ke stem)', '(mizenkei)', "('a' stem)", '(izenkei)'}  # never the end of a word
RARE_FREQ = 10000  # frequency rank: はむ (食む) is ~27000, は行 ~280000, everyday words like 座る or もう are under 1000


def _split(sentence: str, entries_at, longest: bool):
    """(start, end, entries) for each word. longest: longest match (conjugations stay whole); otherwise the most
    common word wins (particles stand alone)."""
    i = 0
    while i < len(sentence):
        entries = entries_at(i)
        best = (entries[0] if entries else None) if longest else _best_entry(entries, sentence[i:])
        n = best.match_len if best and best.match_len else 1
        if n > 1 and sentence[i] in PARTICLES and best.freq > RARE_FREQ:  # は+行 read as は行 (a kana row): split off は
            n = 1
        yield i, i + n, [e for e in entries if e.match_len == n]
        i += n


def _simplest_parse(surface: str, entry, lookup) -> tuple:
    """The shortest list of conjugation steps that turns `entry` into `surface`, outermost first; () if none."""
    dictionary_forms = {entry.written_form, entry.reading} - {''}
    if surface in dictionary_forms:
        return ()
    pos = {p for sense in lookup.dictionary.entries.get(entry.id, []) for p in sense['pos']}
    # a reading that ends on a bare stem is cut off mid-word (疲れたか from 疲れたから read as the 〜たか of 〜たかった)
    parses = [form.process for form in lookup.deconjugator.deconjugate(surface)
              if form.text in dictionary_forms and (not form.tags or form.tags[-1] in pos)
              and not (form.process and form.process[0] in CUT_OFF_STEMS)]
    return min(parses, key=lambda p: (len(p), p), default=())


def _stem_in_text(surface: str, entry) -> bool:
    """読む fits 読める (stem 読 is in the text); 抱く does not fit だけ (a one-kana stem proves nothing)."""
    for form in (entry.written_form, entry.reading):
        stem = form[:-1] if form else ''
        if stem and surface.startswith(stem) and (_KANJI.search(stem) or len(stem) >= 2):
            return True
    return False


def _means_able(entry, lookup) -> bool:
    """読める ('to be able to read') and 使える ('to be usable') are potential forms that became dictionary words."""
    return any('able' in gloss for sense in lookup.dictionary.entries.get(entry.id, []) for gloss in sense['glosses'])


def _conjugation_steps(surface: str, readings, lookup) -> list:
    """(step, point) pairs for a word, innermost step first (食べさせられた: causative, then passive).
    If the likeliest reading has no grammar, other readings whose stem is in the text are tried: 読める -> 読む +
    potential, 休ませて -> 休む + causative. Potential is only taken when the dictionary word itself means "able"
    (読める: to be able to read), because look-alikes are often verbs of their own (叶える: to grant, not 'can come true')."""
    if not readings:
        return []
    top = readings[0]
    potential_ok = not _simplest_parse(surface, top, lookup) and _means_able(top, lookup)
    candidates = readings[:1] + [e for e in readings[1:] if _stem_in_text(surface, e)]
    for i, entry in enumerate(candidates):
        steps = [s for s in reversed(_simplest_parse(surface, entry, lookup)) if s in CONJUGATION_POINTS]
        if i > 0 and not potential_ok:
            steps = [s for s in steps if s != 'potential']
        if steps:
            return [(s, CONJUGATION_POINTS[s]) for s in steps]
    return []


def find_grammar(sentence: str, lookup) -> list[GrammarPoint]:
    """Grammar points in `sentence`, in the order they appear, each listed once."""
    cache = {}

    def entries_at(i):
        # _do_lookup, not lookup(): lookup() shares a cache with the lookup thread
        if i not in cache:  # fixed tie-break: the dictionary returns equally likely readings in random order
            cache[i] = sorted(lookup._do_lookup(sentence[i:i + MAX_WORD_LEN]),
                              key=lambda e: (-e.match_len, -e.priority, e.id))
        return cache[i]

    word_starts = {start for start, _, _ in _split(sentence, entries_at, longest=False)}
    words = list(_split(sentence, entries_at, longest=True))
    conjugated = [(start, end) for start, end, readings in words
                  if readings and _simplest_parse(sentence[start:end], readings[0], lookup)]

    # word-like phrases need a word start, and not one inside a conjugated word (って in 座って)
    phrases = [(m.start(), m.end(), phrase) for regex, phrase in _COMPILED for m in regex.finditer(sentence)
               if not phrase.at_word_start or (m.start() in word_starts
                                               and not any(s < m.start() < e for s, e in conjugated))]
    # a phrase inside a longer one is part of it (ように inside ようにする)
    phrases = [(s, e, p) for s, e, p in phrases
               if not any(s2 <= s and e <= e2 and e2 - s2 > e - s for s2, e2, _ in phrases)]

    found = [(s, p.point) for s, e, p in phrases]
    for start, end, readings in words:
        for step, point in _conjugation_steps(sentence[start:end], readings, lookup):
            if not any(step in p.hides and s < end and start < e for s, e, p in phrases):
                found.append((start, point))

    return list(dict.fromkeys(point for _, point in sorted(found, key=lambda f: f[0])))

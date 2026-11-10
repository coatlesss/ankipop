# meikipop/dictionary/furigana.py
import html
import re

KANJI = r'[一-鿿々〆ヶ]'  # kanji plus 々 〆 ヶ
KANJI_RUN = re.compile(f'{KANJI}+')
SPLIT_KANJI_RUNS = re.compile(f'({KANJI}+)')
MAX_WORD_LEN = 12  # longest word tried at each position, keeps a whole-sentence lookup quick


def _hira(text: str) -> str:
    return ''.join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in text)


def kanji_readings(written: str, reading: str):
    """Splits `reading` over the kanji runs of `written`, using the kana in between as anchors:
    ('食べる', 'たべる') -> ['た'], ('引き出し', 'ひきだし') -> ['ひ', 'だ']. None if they don't line up."""
    pattern = ''.join('(.+?)' if KANJI_RUN.fullmatch(part) else re.escape(_hira(part))
                      for part in SPLIT_KANJI_RUNS.split(written) if part)
    match = re.fullmatch(pattern, _hira(reading))
    return list(match.groups()) if match else None


def _word_html(surface: str, entry) -> str:
    if not entry or not KANJI_RUN.search(surface) or not entry.written_form or not entry.reading:
        return html.escape(surface)
    readings = kanji_readings(entry.written_form, entry.reading)
    # a conjugated surface (食べた) shares its kanji with the dictionary form (食べる); anything else is left bare
    if readings is None or KANJI_RUN.findall(surface) != KANJI_RUN.findall(entry.written_form):
        return html.escape(surface)
    readings = iter(readings)
    return ''.join(f'<ruby>{html.escape(part)}<rt>{html.escape(next(readings))}</rt></ruby>'
                   if KANJI_RUN.fullmatch(part) else html.escape(part)
                   for part in SPLIT_KANJI_RUNS.split(surface) if part)


def _best_entry(entries, text: str):
    """The longest match decides which kanji belong to one word (手紙 stays てがみ, not 手+紙); among matches covering
    those same kanji the most common reading wins (今日は is 今日(きょう)+は, not the greeting こんにちは)."""
    if not entries:
        return None
    kanji = KANJI_RUN.findall(text[:entries[0].match_len])
    same_kanji = [e for e in entries if KANJI_RUN.findall(text[:e.match_len]) == kanji]
    return max(same_kanji, key=lambda e: e.priority)


def furigana_html(text: str, lookup) -> str:
    """`text` as HTML with <ruby> furigana over its kanji, reading each word the way the popup would
    (longest dictionary match at each position, best-ranked entry)."""
    out = []
    i = 0
    while i < len(text):
        if not KANJI_RUN.search(text, i):  # no kanji left: nothing more to annotate
            out.append(html.escape(text[i:]))
            break
        # _do_lookup, not lookup(): lookup() shares a cache with the lookup thread
        entry = _best_entry(lookup._do_lookup(text[i:i + MAX_WORD_LEN]), text[i:])
        length = entry.match_len if entry and entry.match_len else 1
        out.append(_word_html(text[i:i + length], entry))
        i += length
    return ''.join(out)

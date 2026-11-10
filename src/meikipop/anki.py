# meikipop/anki.py
import base64
import hashlib
import html
import io
import logging
import threading
import time

import requests
from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard

from meikipop.config.config import config, APP_NAME
from meikipop.dictionary.customdict import DEFAULT_FREQ
from meikipop.dictionary.furigana import furigana_html
from meikipop.dictionary.lookup import DictionaryEntry
from meikipop.gui.input import to_pynput_hotkey
from meikipop.translate import sentence_span

logger = logging.getLogger(__name__)

ANKI_CONNECT_URL = 'http://127.0.0.1:8765'
TATOEBA_URL = 'https://api.tatoeba.org/unstable/sentences'  # shortcut: "unstable" api may change, switch to a stable version once tatoeba publishes one
JPOD_URL = 'https://assets.languagepod101.com/dictionary/japanese/audiomp3.php'
JPOD_MISSING_MD5 = '7e2c2f954ef6051373ba916f000168dc'  # jpod's "this audio is not available" clip
JPOD_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}  # jpod answers 403 to non-browser user agents

MODEL_NAME = 'meikipop'
FIELDS = ['Word', 'Reading', 'Meaning', 'Sentence', 'SentenceMeaning', 'Picture', 'Audio', 'Frequency', 'Context']
FRONT = '<div class="word">{{Word}}</div>'
BACK = """{{FrontSide}}
<hr id=answer>
<div class="reading">{{Reading}}</div>
{{Audio}}
<div class="meaning">{{Meaning}}</div>
{{#Context}}<div class="sentence">{{Context}}</div>{{/Context}}
{{#Picture}}<div class="picture">{{Picture}}</div>{{/Picture}}
{{#Sentence}}<div class="example">{{Sentence}}</div><div class="translation">{{SentenceMeaning}}</div>{{/Sentence}}
{{#Frequency}}<div class="freq">frequency #{{Frequency}}</div>{{/Frequency}}"""
CSS = """.card { font-family: "Noto Sans JP", "Yu Gothic", "Hiragino Sans", "Meiryo", sans-serif; font-size: 20px; text-align: center; }
.word { font-size: 48px; }
.reading { font-size: 24px; opacity: 0.8; }
.meaning { margin: 12px 0; }
.meaning ol { display: inline-block; text-align: left; margin: 0; }
.sentence { font-size: 24px; margin-top: 16px; }
.example { font-size: 18px; margin-top: 16px; }
.translation { font-size: 16px; opacity: 0.6; }
.picture img { max-width: 100%; max-height: 360px; margin-top: 12px; border-radius: 6px; }
.freq { font-size: 12px; opacity: 0.5; margin-top: 8px; }"""


def context_html(text: str, index: int, match_len: int, lookup=None) -> str:
    """The on-screen sentence around `index`, with the looked-up word (match_len chars from index) in bold.
    With a `lookup`, the rest of the sentence gets furigana; the word itself doesn't, so the card still tests it."""
    start, end = sentence_span(text, index)
    word_end = min(index + match_len, end)
    rest = (lambda s: furigana_html(s, lookup)) if lookup else html.escape
    return (rest(text[start:index]) + '<b>' + html.escape(text[index:word_end]) + '</b>'
            + rest(text[word_end:end])).strip()


def known_word_query(word: str, fields) -> str:
    """Anki search for notes whose field (any of `fields`) is exactly `word`."""
    escaped = ''.join('\\' + c if c in '\\"*_' else c for c in word)
    return ' OR '.join(f'"{field}:{escaped}"' for field in fields)


def format_meaning(entry: DictionaryEntry, all_meanings: bool) -> str:
    if not all_meanings:
        return '; '.join(s['glosses'][0] for s in entry.senses if s.get('glosses'))
    items = []
    for s in entry.senses:
        if not s.get('glosses'):
            continue
        pos = f"<i>({', '.join(s['pos'])})</i> " if s.get('pos') else ''
        items.append(f"<li>{pos}{', '.join(s['glosses'])}</li>")
    return f"<ol>{''.join(items)}</ol>"


def format_meanings(entries, all_meanings: bool) -> str:
    """Meaning field for one entry, or for several readings of a word, each labelled with its reading."""
    if len(entries) == 1:
        return format_meaning(entries[0], all_meanings)
    return ''.join(f"<div>【{e.reading or e.written_form}】 {format_meaning(e, all_meanings)}</div>" for e in entries)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def anki_request(action: str, **params):
    response = requests.post(ANKI_CONNECT_URL, json={'action': action, 'version': 6, 'params': params}, timeout=15).json()
    if response.get('error'):
        raise RuntimeError(response['error'])
    return response.get('result')


class AnkiKnownWords:
    """Remembers which words already have a note in Anki, matched against the first field of every note type
    (Word for meikipop cards, Expression for Lapis, ...). Checks run on a background thread so the popup never waits."""
    RETRY_SECONDS = 30  # after Anki was unreachable, don't try again for this long

    def __init__(self):
        self.version = 0  # bumped whenever an answer arrives, so the popup knows to redraw
        self._known = {}  # word -> bool  # shortcut: cached for the session, notes deleted in Anki stay marked until restart
        self._pending = set()
        self._first_fields = None
        self._offline_until = 0.0
        self._worker = None
        self._lock = threading.Lock()

    def status(self, words) -> dict:
        """{word: True/False} for words already checked; starts a background check for the rest."""
        with self._lock:
            todo = [w for w in words if w and w not in self._known and w not in self._pending]
            if todo and time.time() >= self._offline_until:
                self._pending.update(todo)
                if self._worker is None:
                    self._worker = threading.Thread(target=self._check_pending, daemon=True, name="AnkiKnownWords")
                    self._worker.start()
            return {w: self._known[w] for w in words if w in self._known}

    def mark_known(self, word: str):
        with self._lock:
            self._known[word] = True
            self.version += 1

    def _check_pending(self):
        while True:
            with self._lock:
                if not self._pending:
                    self._worker = None
                    return
                word = self._pending.pop()
            try:
                if self._first_fields is None:
                    self._first_fields = sorted({'Word'} | {anki_request('modelFieldNames', modelName=m)[0]
                                                            for m in anki_request('modelNames')})
                known = bool(anki_request('findNotes', query=known_word_query(word, self._first_fields)))
            except RuntimeError as e:  # anki answered with an error for this word: treat it as not known
                logger.debug(f"Anki: known-word check failed for {word}: {e}")
                known = False
            except Exception:
                with self._lock:  # anki closed or no AnkiConnect: give up quietly and retry later
                    self._pending.clear()
                    self._offline_until = time.time() + self.RETRY_SECONDS
                    self._worker = None
                return
            with self._lock:
                self._known[word] = known
                self.version += 1


known_words = AnkiKnownWords()


class AnkiExporter(QObject):
    """Adds the word shown in the popup to Anki (via the AnkiConnect add-on) when the anki hotkey is pressed."""
    notify = pyqtSignal(str, str)  # (title, message), shown as a tray notification

    def __init__(self, popup_window, screen_manager, shared_state, lookup):
        super().__init__()
        self.popup_window = popup_window
        self.screen_manager = screen_manager
        self.shared_state = shared_state
        self.lookup = lookup  # dictionary, used to read the sentence for furigana
        self.listener = None
        self.reapply_settings()

    def reapply_settings(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
        try:
            self.listener = keyboard.GlobalHotKeys({
                to_pynput_hotkey(config.anki_hotkey): self._on_hotkey,
                to_pynput_hotkey(config.anki_select_hotkey): self.popup_window.select_next_entry,
            })
            self.listener.start()
            logger.info(f"Anki: press '{config.anki_hotkey}' to add the word in the popup to deck '{config.anki_deck}', "
                        f"'{config.anki_select_hotkey}' to pick a different entry.")
        except ValueError:
            logger.error(f"Anki: invalid hotkey '{config.anki_hotkey}' or '{config.anki_select_hotkey}'. "
                         f"Use e.g. 'alt+a', 'ctrl+shift+e' or 'f8'.")
            self.notify.emit(APP_NAME, "Invalid Anki hotkey, check Settings > Anki")

    def _on_hotkey(self):
        # runs on the keyboard hook thread: grab what's on screen now, do the slow network work elsewhere
        if not self.popup_window.is_visible:
            logger.info(f"Anki: '{config.anki_hotkey}' pressed, but no popup is showing. Hover a word first.")
            return
        entries = self.popup_window.selected_entries()
        if not entries:
            logger.info(f"Anki: '{config.anki_hotkey}' pressed, but the popup has no word entry to add.")
            return
        threading.Thread(target=self.add_card, args=(entries, self.screen_manager.last_screenshot,
                                                     self.shared_state.last_hit),
                         daemon=True, name="AnkiExport").start()

    def _context(self, entry: DictionaryEntry, hit) -> str:
        if not hit:
            return ''
        if config.anki_furigana:
            try:
                return context_html(hit[0], hit[1], entry.match_len, self.lookup)
            except Exception as e:  # furigana is a nice-to-have: fall back to the plain sentence
                logger.warning(f"Anki: could not add furigana to the sentence: {e}")
        return context_html(hit[0], hit[1], entry.match_len)

    @staticmethod
    def _ensure_model():
        if MODEL_NAME not in anki_request('modelNames'):
            anki_request('createModel', modelName=MODEL_NAME, inOrderFields=FIELDS, css=CSS,
                         cardTemplates=[{'Name': 'Recognition', 'Front': FRONT, 'Back': BACK}])
            return
        existing = anki_request('modelFieldNames', modelName=MODEL_NAME)
        missing = [f for f in FIELDS if f not in existing]
        if missing:  # note type made by an older version of this feature: add the new fields and show them on the card
            for field in missing:
                anki_request('modelFieldAdd', modelName=MODEL_NAME, fieldName=field)
            anki_request('updateModelTemplates',
                         model={'name': MODEL_NAME, 'templates': {'Recognition': {'Front': FRONT, 'Back': BACK}}})
            anki_request('updateModelStyling', model={'name': MODEL_NAME, 'css': CSS})
            logger.info(f"Anki: added {missing} to the '{MODEL_NAME}' note type")

    def add_card(self, entries: list, screenshot, hit=None):
        """Adds one card for `entries`: a single picked entry, or every reading of the same word."""
        entry = entries[0]
        word = entry.written_form or entry.reading
        try:
            context = self._context(entry, hit)  # here, not on the hotkey thread: furigana takes many lookups
            self._ensure_model()
            anki_request('createDeck', deck=config.anki_deck)  # no-op if the deck exists

            note = {
                'deckName': config.anki_deck,
                'modelName': MODEL_NAME,
                'fields': {
                    'Word': word,
                    'Reading': '・'.join(r for r in dict.fromkeys(e.reading for e in entries) if r and r != word),
                    'Meaning': format_meanings(entries, config.anki_all_meanings),
                    'Frequency': str(entry.freq) if config.anki_frequency and entry.freq < DEFAULT_FREQ else '',
                    'Context': context,
                },
                'options': {'allowDuplicate': False},
                'tags': [APP_NAME],
            }
            # check for duplicates before spending time on downloads
            if not anki_request('canAddNotes', notes=[note])[0]:
                known_words.mark_known(word)
                self.notify.emit(APP_NAME, f"{word} is already in Anki")
                return

            # extras are best effort: a failed download still adds the card
            try:
                note['fields']['Sentence'], note['fields']['SentenceMeaning'] = self._example_sentence(word)
            except Exception as e:
                logger.warning(f"Anki: could not fetch an example sentence for {word}: {e}")
            if screenshot:
                note['picture'] = [{'data': _b64(self._screenshot_jpeg(screenshot)),
                                    'filename': f'{APP_NAME}_{int(time.time() * 1000)}.jpg', 'fields': ['Picture']}]
            if config.anki_audio:
                try:
                    audio = self._pronunciation_mp3(word, entry.reading or word)
                    if audio:
                        note['audio'] = [{'data': _b64(audio), 'filename': f'{APP_NAME}_{word}_{entry.reading}.mp3',
                                          'fields': ['Audio']}]
                except Exception as e:
                    logger.warning(f"Anki: could not fetch audio for {word}: {e}")

            anki_request('addNote', note=note)
            known_words.mark_known(word)
            logger.info(f"Anki: added {word} to '{config.anki_deck}'")
            self.notify.emit(APP_NAME, f"Added {word} to {config.anki_deck}")
        except requests.ConnectionError:
            logger.error("Anki: could not connect. Is Anki running with the AnkiConnect add-on installed?")
            self.notify.emit(APP_NAME, "Could not reach Anki. Is Anki open with AnkiConnect installed?")
        except Exception as e:
            logger.exception(f"Anki: failed to add {word}")
            self.notify.emit(APP_NAME, f"Could not add {word}: {e}")

    @staticmethod
    def _example_sentence(word: str) -> tuple[str, str]:
        params = {'lang': 'jpn', 'q': f'={word}', 'trans:lang': 'eng', 'sort': 'relevance', 'limit': 1}
        data = requests.get(TATOEBA_URL, params=params, timeout=10).json()['data']
        if not data:
            return '', ''
        sentence = data[0]
        translation = next((t['text'] for t in sentence.get('translations', []) if t.get('lang') == 'eng'), '')
        return sentence['text'].replace(word, f'<b>{word}</b>'), translation

    @staticmethod
    def _pronunciation_mp3(word: str, reading: str):
        response = requests.get(JPOD_URL, params={'kanji': word, 'kana': reading}, headers=JPOD_HEADERS, timeout=10)
        response.raise_for_status()
        if hashlib.md5(response.content).hexdigest() == JPOD_MISSING_MD5:
            return None
        return response.content

    @staticmethod
    def _screenshot_jpeg(screenshot) -> bytes:
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img.thumbnail((1280, 1280))  # keeps the anki collection small
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=85)
        return buf.getvalue()

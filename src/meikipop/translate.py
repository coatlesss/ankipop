# meikipop/translate.py
import logging
import threading

import requests
from pynput import keyboard

from meikipop.config.config import config
from meikipop.dictionary.lookup import SentenceTranslation
from meikipop.gui.input import to_pynput_hotkey

logger = logging.getLogger(__name__)

GOOGLE_TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'  # shortcut: free unofficial endpoint, may get rate-limited or change; switch to the paid Cloud Translation API if it breaks
SENTENCE_ENDS = '。！？!?'
LEADING_JUNK = '」』）)］] 　\n'  # closing brackets left over from the previous sentence


def sentence_span(text: str, index: int) -> tuple[int, int]:
    """(start, end) of the sentence in `text` that contains the character at `index`."""
    start = max(text.rfind(c, 0, index) for c in SENTENCE_ENDS) + 1
    while start < index and text[start] in LEADING_JUNK:
        start += 1
    ends = [pos for pos in (text.find(c, index) for c in SENTENCE_ENDS) if pos != -1]
    return start, (min(ends) + 1 if ends else len(text))


def sentence_at(text: str, index: int) -> str:
    """Returns the sentence of `text` that contains the character at `index`."""
    start, end = sentence_span(text, index)
    return text[start:end].strip()


def translate(text: str) -> str:
    params = {'client': 'gtx', 'sl': 'ja', 'tl': 'en', 'dt': 't', 'q': text}
    response = requests.get(GOOGLE_TRANSLATE_URL, params=params, timeout=10)
    response.raise_for_status()
    return ''.join(part[0] for part in response.json()[0] if part[0])  # long text comes back in several parts


class SentenceTranslator:
    """Shows a translation of the sentence under the mouse in the popup when the translate hotkey is pressed."""

    def __init__(self, popup_window, shared_state):
        self.popup_window = popup_window
        self.shared_state = shared_state
        self.listener = None
        self.reapply_settings()

    def reapply_settings(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
        try:
            self.listener = keyboard.GlobalHotKeys({to_pynput_hotkey(config.translate_hotkey): self._on_hotkey})
            self.listener.start()
            logger.info(f"Translate: press '{config.translate_hotkey}' to translate the sentence under the mouse.")
        except ValueError:
            logger.error(f"Translate: invalid hotkey '{config.translate_hotkey}'. Use e.g. 'alt+t', 'ctrl+shift+t' or 'f9'.")

    def _on_hotkey(self):
        # runs on the keyboard hook thread: grab the sentence now, translate elsewhere
        hit = self.shared_state.last_hit
        if not self.popup_window.is_visible or not hit:
            logger.info(f"Translate: '{config.translate_hotkey}' pressed, but no popup is showing. Hover some text first.")
            return
        text, index, text_block, is_vertical = hit
        threading.Thread(target=self._translate_into_popup, args=(sentence_at(text, index), text_block, is_vertical),
                         daemon=True, name="Translate").start()

    def _translate_into_popup(self, sentence: str, text_block: tuple = (), is_vertical: bool = False):
        pending = [SentenceTranslation(sentence, 'translating…', text_block, is_vertical)]
        self.popup_window.set_latest_data(pending)
        try:
            translation = translate(sentence)
        except Exception as e:
            logger.warning(f"Translate: failed to translate '{sentence}': {e}")
            translation = f'translation failed: {e}'
        result = [SentenceTranslation(sentence, translation, text_block, is_vertical)]
        if self.popup_window.get_latest_data() is pending:  # don't overwrite a newer lookup if the mouse moved on
            self.popup_window.set_latest_data(result)

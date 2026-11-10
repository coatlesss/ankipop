# ankipop - meikipop with anki cards and sentence translation

ankipop is a fork of [meikipop](https://github.com/rtr46/meikipop), the universal japanese ocr popup dictionary. it keeps everything meikipop does (look up japanese words anywhere on your screen: websites, games, scanned manga, hard-coded video subtitles) and adds one-key anki cards and sentence translation.

https://github.com/user-attachments/assets/a1834197-3059-438c-a2dc-716e8ec9078f

> ankipop is a modified version of [meikipop](https://github.com/rtr46/meikipop) by rtr46, based on meikipop 2.0.6 and changed starting november 2026. the changes are listed under [what this fork adds](#what-this-fork-adds).

## what this fork adds

### anki cards

* **one key to make a card:** hover a word and press `alt+a`. ankipop talks to anki through the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on and creates the card in the background.
* **cards come filled in:**
  * the word, its reading and its meaning
  * the sentence you were actually reading, with the word in bold
  * a screenshot of the scan area
  * an example sentence with english translation from [tatoeba](https://tatoeba.org)
  * pronunciation audio from japanesepod101 (optional)
  * the word's frequency rank (optional)
* **furigana on the sentence (optional):** readings over the kanji of the on-screen sentence, except the word you're learning, so the card still tests it.
* **pick the right entry:** `alt+s` steps through the popup's entries (marked with ▶) and `alt+a` adds the marked one. without a pick, every reading of the word goes on one card (e.g. 角: かど・かく・つの・すみ).
* **see what you already know:** words that already have a note in anki get a ✓ in the popup. this checks the first field of every note type, so cards made with other tools (e.g. lapis) count too.
* **no setup in anki:** the first card creates a `meikipop` note type and the deck you chose. adding a word that's already in anki is caught, and every result shows up as a notification.

### sentence translation

* hover a sentence and press `alt+t`. the popup shows the sentence and its english translation (google translate) until you move to another word.

### popups that don't cover the text

* sentence translations sit above or below the text box instead of on top of it.
* for vertical text (manga), word lookups and translations go beside the speech bubble (right side if there's room, since that part is already read) instead of covering the rest of the column.

## features (from meikipop)

*   **works everywhere:** if you can see it on your screen, you can look it up. no more limitations of browser extensions, hooks or application-specific tools.
*   **ocr-powered:** reads japanese text directly from images, making it perfect for games, comics, and videos.
*   **blazingly fast:** the dictionary is pre-processed into a highly optimized format for instant lookups. the ui is designed to be lightweight and responsive.
*   **simple & intuitive:** just point your mouse and press a hotkey. that's it.
*   **highly customizable:** change the hotkey, theme, colors, and layout to create your perfect reading experience.
*   **region or fullscreen:** scan your entire screen or select a specific region (like a game window or manga page) to improve performance.
*   **pluggable ocr backend:** lets you choose whatever ocr suits you best. whether you want the highest accuracy remote ocr, that runs great even on low-end hardware or you want blazingly fast and private local ocr.

## philosophy & limitations

meikipop is designed to do one thing and do it exceptionally well: provide fast, frictionless, on-screen dictionary lookups. ankipop keeps that focus and adds the two things that come right after a lookup: saving the word and understanding the whole sentence.

meikipop is heavily inspired by the philosophy of [Nazeka](https://github.com/wareya/nazeka), a fantastic browser-based popup dictionary, and aims to bring that seamless experience to the entire desktop. it also draws inspiration from the ocr architecture of [owocr](https://github.com/AuroraWright/owocr/tree/master/owocr).

a few things to keep in mind:

*   **anki support is deliberately simple.** one hotkey, one card layout. cards always use the `meikipop` note type; mapping onto your own note types isn't supported.
*   **it is not a multi-dictionary tool.** while meikipop lets you import yomitan dictionaries, it is designed to run best with a single, semi-custom jmdict+kanjidic dictionary.
*   **the new features are tested on windows.** the hotkeys use pynput and should work on linux (x11) and macos, but haven't been tried there.

## installation

there are no prebuilt downloads for ankipop yet, so you run it from source or build the .exe yourself. note that when ankipop is started for the first time, a dictionary and ocr models may be downloaded.

### run from source

you need python 3.10+.

```bash
git clone https://github.com/coatlesss/ankipop.git
cd ankipop
python -m venv .venv
.venv\Scripts\activate        # windows; on linux/macos: source .venv/bin/activate
pip install -e .
meikipop                      # run the application
```

if windows powershell says *running scripts is disabled on this system* when activating, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

because this is an editable install, changes you make under `src/meikipop/` take effect the next time you start the app.

### build a standalone .exe (windows)

with the environment above activated:

```bash
pip install pyinstaller
pyinstaller --noconfirm meikipop.win.x64.spec
```

the result is `dist\meikipop.exe`, a single file you can copy to any windows pc. quit a running meikipop first, or the build can't overwrite the old .exe. after adding new non-python files (icons, json, a new ocr provider), list them in the `.spec` file too.

### just want the original meikipop?

the upstream project has [prebuilt binaries](https://github.com/rtr46/meikipop/releases/latest) and a pypi package (`pip install --upgrade meikipop`). neither includes the features of this fork.

### platform support

* **windows, linux (x11)** - these are the primary supported platforms
* **macos** - supported thanks to community contributions
* **linux (wayland)** - it can work in principle thanks to community contributions, but may require additional trouble shooting

see for platform specific setup details:
<details>
<summary>macos</summary>

* go to **System Preferences** > **Security & Privacy** > **Privacy**
* add/enable your terminal app in **Input Monitoring**, **Screen Recording** and **Accessibility**

note that there may be problems when using python 3.14. use one of [these workarounds](https://github.com/rtr46/meikipop/issues/43) if necessary.
</details>

<details>
<summary>wayland (alpha)</summary>

it is possible to run meikipop on wayland in principle, but depending on your specific setup you may need to take additional steps like installing additional dependencies, fixing some of the wayland specific code or changing some of your setup. since the wayland eco system is terribly fragmented and deliberately prevents apps like meikipop from working natively, don't expect any support, but feel free to open an issue regardless.

here are some tips and recommendations:
* consider switching to x11
* the easiest and most compatible way is trying to run the flatpak distribution of meikipop first, before trying any of the other tips 
* if the flatpak does not work for you, install via pypi or create an editable install and avoid the linux prebuilt, which only got tested on x11
* make sure you have xwayland working
* you may need to install additional python dependencies, depending on your system like `pip install pygobject`
* you may need to install additional os dependencies, depending on your distribution like:
  * fedora: `sudo dnf install libxcb xcb-util xcb-util-cursor libxkbcommon-x11 libxkbcommon xcb-util-wm xcb-util-keysyms pipewire-gstreamer`
  * ubuntu: `sudo apt install cmake libcairo2-dev libgirepository-2.0-dev libgstreamer1.0-dev gstreamer1.0-pipewire libxcb-xkb-dev libxcb-cursor-dev libxcb-xinerama0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1-dev libxcb-shape0`
* if meikipop is running, but doesn't show any popups, make sure to test lookups on a windowed xwayland application like steam
* ask your favorite llm for help
</details>

## how to use

1.  run the application (`meikipop`, or `meikipop.exe` if you built one).
2.  the first time you run the app in `region` mode, you will be prompted to select an area of your screen to scan.
3.  move your mouse over any japanese text on your screen.
4.  a popup with dictionary entries will appear.
5.  **right-click the system tray icon** to open the settings, reselect the scan region, change the ocr provider or quit the application.

### hotkeys

| key | what it does |
|-----|--------------|
| `shift` | show the popup (only needed in manual scan mode, or with "show popup without hotkey" turned off) |
| `alt+t` | translate the sentence under the mouse |
| `alt+a` | add the word in the popup to anki |
| `alt+s` | pick which popup entry `alt+a` adds (▶ marks it) |

all of them can be changed in the settings. the new hotkeys accept combinations like `ctrl+shift+e` or single keys like `f8`. if `alt+a` or `alt+t` seems to do nothing, check the console window: every press is logged with what happened (e.g. *no popup is showing*).

## setting up anki

1.  install [anki](https://apps.ankiweb.net) and open it.
2.  in anki, go to **tools > add-ons > get add-ons**, enter `2055492159` ([AnkiConnect](https://ankiweb.net/shared/info/2055492159)) and restart anki.
3.  keep anki open while you use ankipop.
4.  in ankipop, open **settings > anki**. the status line should say *connected to anki*. pick a deck from the dropdown, or type a new name to create one. press **refresh** after making a new deck in anki.
5.  choose what goes on your cards: pronunciation audio, all meanings, frequency rank and sentence furigana.

good to know:

* the first card creates a `meikipop` note type. if a later version of ankipop adds a field to it and you sync with ankiweb, anki may ask for a one-way sync once; choose **upload** on the computer you mine on.
* the ✓ marks are remembered until you restart ankipop, so a note you delete in anki keeps its ✓ until then.
* duplicates are checked by the written word, so two readings of the same kanji can't become two separate cards. add them together instead (`alt+a` without picking).

## online services

on top of the ocr provider you choose, the new features use these services:

* **google translate**, for `alt+t`. the sentence under your mouse is sent to google. this uses google's free, unofficial endpoint, which could be rate-limited or change.
* **tatoeba**, for example sentences on cards. sentences are licensed [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/) by their tatoeba contributors.
* **japanesepod101**, for pronunciation audio (can be turned off in settings > anki).

word lookups, the ✓ marks and furigana work entirely offline.

## configuration

you can fully customize ankipop's behavior and appearance. right-click the tray icon and choose "settings" to open the configuration gui. the anki options and hotkeys live on the **anki** tab, the translate hotkey on the **general** tab.

changes are saved to a platform-specific user data directory which contains `config.ini` and `dictionary.pkl`:
- windows: `%LOCALAPPDATA%\meikipop\`
- linux: `~/.config/meikipop/`
- macos: `~/Library/Application Support/meikipop/`

ankipop uses the same folder as meikipop, so your settings and dictionary carry over.

## using alternative ocr backends...

meikipop's architecture allows you to choose whatever ocr suits your use case best:
- meikiocr (default/local): possibly the fastest local ocr worth using on cpu and can run even faster on nvidia gpus. primarily designed for video games with horizontal text. poor accuracy for vertical text.
- google lens (remote): high accuracy, but requires an internet connection and has higher latency then the local options.
- chrome screen ai (local): alternative local ocr worth checking out if meikiocr does not fit your use case, e.g. for vertical manga text. requires additional setup ([instructions](https://github.com/rtr46/meikipop/releases/tag/v1.10.0))
- owocr: owocr lets you choose from even more ocr backends (see below)
- custom ocr provider: if you are running from source it is very simple to integrate any ocr provider on your own (see below) 

### ...via owocr provider

owocr lets you run any relevant ocr engine and lets meikipop use it. just run a local [owocr](https://github.com/AuroraWright/owocr/tree/master/owocr) instance and select the owocr ocr provider from meikipop's system tray menu.

make sure you:

* use owocr 1.15.0 or newer
* enable reading from and writing to websockets
* choose the json output format
* and use an ocr backend that supports coordinates (most do)
    ```bash
    pip install -U "owocr>=1.15"
    owocr -r websocket -w websocket -of json -e glens # replace glens with your favorite owocr backend
    ```

### ...via custom ocr provider

you can develop your own ocr provider. to get started, you can copy the `dummy` provider and use it as a template.

for a complete guide, see: [how to create a custom ocr provider](docs/CUSTOM_OCR_PROVIDER.md)

## building your own dictionary (optional)

in case you want to update your dictionary you can simply run:

```bash
meikipop build-dict
```

if you want to import a yomitan dictionary that is possible as well. you can import multiple yomitan dictionaries at once, but be aware that this will overwrite your default dictionary:

```bash
# try to keep as much of the dictionary's original formatting
meikipop import-yomitan-dict-html my_yomitan_dict.zip
# or create a compact, text only dictionary
meikipop import-yomitan-dict-text my_yomitan_dict.zip
# or import multiple dictionaries at once
meikipop import-yomitan-dict-text dict1.zip dict2.zip
```

## running the tests

the new features come with tests that don't need anki or an internet connection:

```bash
python tests/test_anki.py
python tests/test_translate.py
python tests/test_furigana.py
```

## license

ankipop is licensed under the GNU General Public License v3.0, the same license as meikipop. see the `LICENSE` file for the full license text. meikipop is © rtr46 and its contributors.

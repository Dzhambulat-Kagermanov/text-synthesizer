# text-synthesizer

Локальная озвучка markdown-заметок в mp3/wav с субтитрами. Два движка:

| Движок        | Язык             | Сеть     | Качество RU          | Время на 17k символов |
| ------------- | ---------------- | -------- | -------------------- | --------------------- |
| **edge-tts**  | RU + ~100 языков | нужна    | ★★★★★ (Azure Neural) | ~5–15 сек             |
| **Silero v4** | RU               | не нужна | ★★★☆☆                | ~1–3 мин (CPU)        |

- **Русский, быстро и красиво** → `edge-tts` (голоса Azure Neural, бесплатно).
- **Русский, офлайн** → `Silero v4`.

Оба движка создают аудио **и** `.srt` с таймингами.

---

## Содержание

- [Быстрый старт](#быстрый-старт)
- [Установка](#установка)
- [Модели](#модели)
- [Использование](#использование)
- [Голоса](#голоса)
- [Субтитры (SRT)](#субтитры-srt)
- [Интеграция с Obsidian](#интеграция-с-obsidian)
- [Кэш](#кэш)
- [Структура проекта](#структура-проекта)
- [Траблшутинг](#траблшутинг)
- [Лицензии](#лицензии)

---

## Быстрый старт

```powershell
# 1. Зайти в папку проекта
cd C:\Users\you\Desktop\Проекты\tts

# 2. Создать venv и активировать
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Поставить зависимости и скачать модели (одна команда)
python install_models.py

# 4. Озвучить заметку
python tts.py "C:\vault\заметка.md" --engine edge
```

Результат появится **рядом с заметкой**:

```
заметка.ru.edge.5118fceb47.mp3
заметка.ru.edge.5118fceb47.srt
```

---

## Установка

### Требования

- **Python 3.10–3.12** — https://www.python.org/downloads/windows/ (галочка «Add python.exe to PATH»).
- **Windows 10/11**, PowerShell.
- **~250 МБ** на диске: Silero `v4_ru.pt` ~38 МБ + пакеты (`torch` ~200 МБ).
- Для edge-tts — интернет.

### Виртуальное окружение

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Если PowerShell ругается «выполнение скриптов отключено»:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

и активируй заново.

### Зависимости + модели одной командой

```powershell
python install_models.py
```

Скрипт:

1. Проверит пакеты (`langdetect`, `numpy`, `soundfile`, `torch`, `silero`, `edge-tts`) и доставит отсутствующие.
2. Скачает `models/v4_ru.pt` (Silero RU), если его нет или размер битый.
3. Проверит, что edge-tts видит русские голоса (сеть до Microsoft).
4. Напечатает итог и команды запуска.

Идемпотентен: повторный запуск ничего не ломает и не перекачивает.

### Установка вручную

```powershell
pip install -r requirements.txt

# Silero RU модель (~38 МБ)
curl.exe -L "https://models.silero.ai/models/tts/ru/v4_ru.pt" -o "models\v4_ru.pt"
```

`edge-tts` моделей не требует — синтез на серверах Microsoft.

### Проверка

```powershell
python -c "import langdetect, soundfile, numpy, torch, silero, edge_tts; print('все пакеты ok')"
dir models\v4_ru.pt
```

---

## Модели

### Silero RU — `models\v4_ru.pt` (~38 МБ)

```powershell
curl.exe -L "https://models.silero.ai/models/tts/ru/v4_ru.pt" -o "models\v4_ru.pt"
```

Если `curl.exe` нет:

```powershell
Invoke-WebRequest -Uri "https://models.silero.ai/models/tts/ru/v4_ru.pt" -OutFile "models\v4_ru.pt"
```

Проверка: `dir models\v4_ru.pt` → **38–40 МБ**. Меньше 30 МБ — скачивание оборвалось, перекачай.

### edge-tts

Модели не нужны. Нужен только интернет и `pip install edge-tts`.

---

## Использование

### Единый CLI `tts.py`

```powershell
python tts.py "<путь к .md>" [опции]
```

**Опции:**

| Опция      | Значения               | По умолчанию      | Что делает                             |
| ---------- | ---------------------- | ----------------- | -------------------------------------- |
| `--engine` | `edge` \| `silero`     | **меню**          | Движок. Без флага — интерактивное меню |
| `--voice`  | см. [Голоса](#голоса)  | зависит от движка | Голос                                  |
| `--rate`   | `+10%`, `+20%`, `-10%` | `+10%`            | Темп (только edge-tts)                 |

**Что создаётся рядом с заметкой:**

| Движок   | Аудио                              | Субтитры                           |
| -------- | ---------------------------------- | ---------------------------------- |
| `edge`   | `заметка.<lang>.edge.<hash>.mp3`   | `заметка.<lang>.edge.<hash>.srt`   |
| `silero` | `заметка.<lang>.silero.<hash>.wav` | `заметка.<lang>.silero.<hash>.srt` |

### Интерактивное меню (без `--engine`)

```
$ python tts.py "C:\vault\заметка.md"
Язык: ru

Выбери движок:
  1) edge    — RU/др., онлайн, лучшее качество (Azure Neural)
  2) silero  — RU, офлайн
  (язык заметки: ru, рекомендуется: edge)
Номер [1/2] или имя (edge/silero), Enter = рекомендованный:
```

- `Enter` — рекомендованный для языка (`ru → edge`, иначе `edge`).
- `1`/`2` или `edge`/`silero` — явный выбор.
- Язык `unknown` (короткий/смешанный текст) — не блокирует.

### Отдельные движки (без меню)

```powershell
python edge_synth.py   "<путь к .md>" [--voice ru-RU-SvetlanaNeural] [--rate +10%]
python silero_synth.py "<путь к .md>"
```

Удобно для автоматизации и Obsidian Shell commands, где меню нежелательно.

### Примеры запуска

#### 1. Авто-режим с меню

```powershell
python tts.py "C:\vault\заметка.md"
```

#### 2. Явно edge, мужской голос, +20%

```powershell
python tts.py "C:\vault\заметка.md" --engine edge --voice ru-RU-DmitryNeural --rate +20%
```

#### 3. Silero офлайн

```powershell
python tts.py "C:\vault\заметка.md" --engine silero
```

Создаст:

```
заметка.ru.silero.be1d1317f4.wav
заметка.ru.silero.be1d1317f4.srt
```

#### 4. Любой язык через edge-tts

edge-tts поддерживает ~100 языков. Скрипт **не блокирует** по языку — просто передай голос:

```powershell
python tts.py "C:\vault\нотатка.md" --engine edge --voice uk-UA-OstapNeural
python tts.py "C:\vault\notatka.md" --engine edge --voice pl-PL-ZofiaNeural
```

#### 5. Озвучить все заметки в папке

```powershell
Get-ChildItem "C:\vault\DevOps" -Recurse -Filter "*.md" | ForEach-Object {
    python tts.py $_.FullName --engine edge
}
```

#### 6. Проверить язык и длину без синтеза

```powershell
python -c "from common import read_note, detect_lang; from pathlib import Path; _, t = read_note(Path(r'C:\vault\заметка.md')); print('lang:', detect_lang(t), '| chars:', len(t))"
```

#### 7. Очистить кэш для заметки

```powershell
Remove-Item "C:\vault\заметка.*.mp3","C:\vault\заметка.*.wav","C:\vault\заметка.*.srt" -ErrorAction SilentlyContinue
```

---

## Голоса

### edge-tts — список доступных

Все голоса:

```powershell
python -c "import asyncio, edge_tts; [print(v['ShortName']) for v in asyncio.run(edge_tts.list_voices())]"
```

Только русские:

```powershell
python -c "import asyncio, edge_tts; [print(v['ShortName']) for v in asyncio.run(edge_tts.list_voices()) if v['Locale'].startswith('ru-')]"
```

Обычно доступны:

| Голос                  | Пол  | Замечание         |
| ---------------------- | ---- | ----------------- |
| `ru-RU-SvetlanaNeural` | жен. | дефолт, спокойный |
| `ru-RU-DmitryNeural`   | муж. | живой, чёткий     |

> Голос `ru-RU-DariyaNeural` Microsoft убрал. Если скрипт падает с `NoAudioReceived` — проверь актуальный список командой выше.

Примеры голосов других языков:

| Язык        | Голоса                                                     |
| ----------- | ---------------------------------------------------------- |
| Украинский  | `uk-UA-OstapNeural`, `uk-UA-PolinaNeural`                  |
| Польский    | `pl-PL-ZofiaNeural`, `pl-PL-MarekNeural`                   |
| Немецкий    | `de-DE-KatjaNeural`, `de-DE-ConradNeural`                  |
| Французский | `fr-FR-DeniseNeural`, `fr-FR-HenriNeural`                  |
| Английский  | `en-US-AriaNeural`, `en-US-GuyNeural`, `en-GB-SoniaNeural` |

### Silero v4 — русские голоса

| Голос     | Пол           |
| --------- | ------------- |
| `baya`    | жен. (дефолт) |
| `kseniya` | жен.          |
| `eugene`  | муж.          |
| `aidar`   | муж.          |

Сменить голос Silero (в `tts.py` дефолт `baya`):

```powershell
python -c "from silero_synth import tts_file; from pathlib import Path; print(tts_file(Path(r'C:\vault\заметка.md'), speaker='eugene'))"
```

---

## Субтитры (SRT)

Оба движка создают `.srt` рядом с аудио. Имя совпадает с аудиофайлом.

| Движок   | Гранулярность         | Как получается                                                    |
| -------- | --------------------- | ----------------------------------------------------------------- |
| `edge`   | по фразам (5–10 слов) | из `WordBoundary`-событий edge-tts, группировка по паузам/длине   |
| `silero` | по предложениям       | синтез по предложениям, тайминги точные (по длительности каждого) |

### Настройка группировки (edge)

В `edge_synth.py`:

```python
srt_entries = _group_words_into_phrases(
    all_words,
    max_words=10,      # макс слов в строке
    max_chars=80,      # макс символов в строке
    max_gap=0.4,       # пауза (сек), после которой новый субтитр
    max_duration=6.0,  # макс длительность субтитра
)
```

- Длиннее строки → `max_words=14`, `max_chars=100`.
- Короче строки → `max_words=6`, `max_chars=60`.

### Настройка Silero

В `silero_synth.py`:

```python
SENTENCE_PAUSE = 0.30   # пауза между предложениями (сек)
MIN_SENT_CHARS = 8      # короче — приклеивать к предыдущему
MAX_SENT_CHARS = 220    # длиннее — резать по запятым
```

### Просмотр субтитров

- **Obsidian**: плагин **Recording Transcript Player** (включи «Open matched recordings in the plugin view») или **Media Extended**.
- **VLC**: открыть mp3 — srt подхватится автоматически.
- **mpv**: `mpv --sub-file=заметка.srt заметка.mp3`.

---

## Интеграция с Obsidian

### Вариант 1: Shell commands (горячая клавиша)

1. **Settings → Community plugins → Browse** → **Shell commands** → Install → Enable.
2. **Settings → Shell commands → New command**:
   - **Command**: `python C:\Users\you\Desktop\Проекты\tts\tts.py "{{file_path}}" --engine edge`
   - **Working directory**: `C:\Users\you\Desktop\Проекты\tts`
3. **Settings → Hotkeys** → назначь, например, `Ctrl+Alt+S`.

Теперь `Ctrl+Alt+S` в заметке → mp3+srt рядом → слушаешь.

### Вариант 2: внешний watcher

`watch.ps1` в корне проекта (запускать в отдельном окне PowerShell):

```powershell
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = "C:\Users\you\Documents\Obsidian-knowledge-base"
$watcher.Filter = "*.md"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

$action = {
    $path = $Event.SourceEventArgs.FullPath
    Start-Sleep -Seconds 2
    python "C:\Users\you\Desktop\Проекты\tts\tts.py" "$path" --engine edge
}
Register-ObjectEvent $watcher Changed -Action $action
Register-ObjectEvent $watcher Created -Action $action

while ($true) { Start-Sleep -Seconds 5 }
```

---

## Кэш

Имя файла: `заметка.<lang>.<engine>.<hash>.<ext>`.

- `<lang>` — определённый язык (или `unknown` для коротких/смешанных текстов).
- `<engine>` — `edge` / `silero`.
- `<hash>` — md5 от текста + языка + движка.

Правила:

- Тот же текст + движок → тот же файл → повторный запуск **мгновенный**.
- Правишь заметку → хэш меняется → генерится заново.
- Меняешь движок → новый файл (старый не мешает).
- Пустые файлы (0 байт) не считаются кэшем.

Очистить кэш для заметки:

```powershell
Remove-Item "C:\vault\заметка.*.mp3","C:\vault\заметка.*.wav","C:\vault\заметка.*.srt" -ErrorAction SilentlyContinue
```

Очистить весь кэш в папке:

```powershell
Get-ChildItem "C:\vault" -Recurse -Include "*.ru.edge.*.mp3","*.ru.edge.*.srt","*.ru.silero.*.wav","*.ru.silero.*.srt" | Remove-Item
```

---

## Структура проекта

```
tts\
├── tts.py               # единый CLI: --engine edge|silero, меню
├── common.py            # clean_md, split_text, detect_lang, cache_path, write_srt
├── edge_synth.py        # edge-tts (онлайн) + SRT (по фразам)
├── silero_synth.py      # Silero v4 (офлайн) + SRT (по предложениям)
├── install_models.py    # установка пакетов + скачивание v4_ru.pt
├── requirements.txt
├── README.md
├── .gitignore
├── models\              # веса (в .gitignore)
│   └── v4_ru.pt
└── cache\               # промежуточный кэш
```

### `requirements.txt`

```
langdetect>=1.0.9
numpy>=1.24
soundfile>=0.12
torch>=2.0
silero>=0.5.5
edge-tts>=7.0
```

### `.gitignore`

```
.venv/
venv/
__pycache__/
*.pyc
models/*.pt
models/*.onnx
models/*.bin
cache/
_edge_tmp/
*.wav
*.mp3
*.srt
```

---

## Траблшутинг

| Симптом                                          | Причина                                       | Решение                                                                                                   |
| ------------------------------------------------ | --------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `No module named 'langdetect'`                   | pip не в тот интерпретатор                    | активируй venv, `python -m pip install -r requirements.txt`                                               |
| `NoAudioReceived` (edge)                         | голос удалён / длина / сеть                   | `list_voices()`, проверь голос; нарезка включена; `Test-NetConnection speech.platform.bing.com -Port 443` |
| mp3 на 2 минуты вместо 15                        | старый код без нарезки                        | используй `edge_synth.py` из этого репо (split_text + проверка `size > 0`)                                |
| `RuntimeError: ... v4_ru.pt No such file`        | кириллица в пути (баг torch)                  | `silero_synth.py` копирует `.pt` в `C:/Temp/silero_tts_local/`                                            |
| `size of tensor a (16622) must match b (5000)`   | текст Silero > ~900 символов                  | `silero_synth.py` режет автоматически                                                                     |
| `Model couldn't generate your text`              | то же                                         | то же                                                                                                     |
| `FileNotFoundError: ...silero-models\hubconf.py` | нет папки                                     | не нужно: используется `PackageImporter` + локальный `.pt`                                                |
| SRT пустой / 0 байт                              | edge не вернул WordBoundary                   | в `edge_synth.py` проверка `len(srt_entries)`; при пустоте `.srt` удаляется                               |
| SRT очень короткие строки                        | word-level без группировки                    | `_group_words_into_phrases` в `edge_synth.py` (по умолчанию 5–10 слов)                                    |
| Silero SRT «уезжает»                             | делим время фрагмента пропорционально         | синтез по предложениям (в `silero_synth.py`), тайминги точные                                             |
| Меню не появляется                               | передан `--engine`                            | убери `--engine`                                                                                          |
| Язык `cy`/`unknown`                              | langdetect шумит на коротком/смешанном тексте | не ошибка; выбери движок вручную                                                                          |
| `Recording Transcript Player` не видит srt       | автопереключение выключено                    | Settings плагина → «Open matched recordings in the plugin view»                                           |

---

## Лицензии

- **edge-tts** — неофициальный клиент к Microsoft Edge Read Aloud. Формальных лимитов нет, но возможен rate limit при массовых запросах. Не для коммерческого распространения; сервис может быть прикрыт в любой момент.
- **Silero v4** — бесплатно для некоммерческого использования (см. лицензию Silero).
- **Код этого репозитория** — MIT.

## Благодарности

- [edge-tts](https://github.com/rany2/edge-tts) — rany2
- [Silero Models](https://github.com/snakers4/silero-models) — Snakers4

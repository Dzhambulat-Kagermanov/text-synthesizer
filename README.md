# kokoro-tts

Локальная озвучка заметок Obsidian (и любых markdown-файлов) в mp3/wav.
Три движка, каждый можно использовать отдельно или через единый CLI:

| Движок        | Язык       | Сеть     | Качество RU          | Время на 17k символов |
| ------------- | ---------- | -------- | -------------------- | --------------------- |
| **edge-tts**  | RU (и др.) | нужна    | ★★★★★ (Azure Neural) | ~5–15 сек             |
| **Silero v4** | RU         | не нужна | ★★★☆☆                | ~1–3 мин (CPU)        |
| **Kokoro**    | EN         | не нужна | —                    | ~2–5 мин (CPU)        |

Русские заметки → edge-tts (быстро, красиво) или Silero (офлайн).

---

## Содержание

- [Быстрый старт](#быстрый-старт)
- [Установка](#установка)
- [Модели](#модели)
- [Использование](#использование)
  - [Единый CLI `tts.py`](#единый-cli-ttspy)
  - [Отдельные движки](#отдельные-движки)
  - [Примеры запуска](#примеры-запуска)
- [Голоса](#голоса)
- [Субтитры (SRT) и подсветка в Obsidian](#субтитры-srt-и-подсветка-в-obsidian)
- [Интеграция с Obsidian](#интеграция-с-obsidian)
- [Кэш](#кэш)
- [Структура проекта](#структура-проекта)
- [Траблшутинг](#траблшутинг)
- [Лицензии и условия](#лицензии-и-условия)

---

## Быстрый старт

```powershell
# 1. Клонировать / распаковать проект, зайти в папку
cd tts-project-path

# 2. Создать venv и активировать
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Поставить зависимости
pip install -r requirements.txt

# 4. Озвучить заметку
python tts.py "C:\vault\заметка.md"
```

## Использование

### Единый CLI `tts.py`

```powershell
python tts.py "<путь к .md>" [опции]
```

**Опции:**

| Опция      | Значения               | По умолчанию      | Что делает                                                                |
| ---------- | ---------------------- | ----------------- | ------------------------------------------------------------------------- |
| `--engine` | `edge` \| `silero`     | **меню**          | Движок синтеза. Если не указан — интерактивное меню с подсказкой по языку |
| `--voice`  | см. [Голоса](#голоса)  | зависит от движка | Голос                                                                     |
| `--rate`   | `+10%`, `+20%`, `-10%` | `+10%`            | Темп (только edge-tts)                                                    |

**Что создаётся рядом с заметкой:**

| Движок   | Аудио                              | Субтитры                                           |
| -------- | ---------------------------------- | -------------------------------------------------- |
| `edge`   | `заметка.<lang>.edge.<hash>.mp3`   | `заметка.<lang>.edge.<hash>.srt` (word-level)      |
| `silero` | `заметка.<lang>.silero.<hash>.wav` | `заметка.<lang>.silero.<hash>.srt` (по фрагментам) |

SRT у edge — **по словам** (из WordBoundary). У silero/kokoro — **по фрагментам** (1 кусок = 1 субтитр), т.к. эти модели не отдают word-level тайминги.

### Интерактивное меню (без `--engine`)

Если запустить без `--engine`, скрипт спросит движок:

```
$ python tts.py "C:\vault\заметка.md"
Язык: ru

Выбери движок:
  1) edge    — RU/др., онлайн, лучшее качество (Azure Neural)
  2) silero  — RU, офлайн
  3) kokoro  — EN, офлайн
  (язык заметки: ru, рекомендуется: edge)
Номер [1/2/3] или имя (edge/silero/kokoro), Enter = рекомендованный:
```

- `Enter` — берёт рекомендованный для языка (`ru → edge`, `en → kokoro`, иначе `edge`).
- `1`/`2`/`3` или `edge`/`silero`/`kokoro` — явный выбор.
- Язык `unknown` (короткий/смешанный текст) — не блокирует, просто рекомендация `edge`.

### Отдельные движки (без меню, всегда явный движок)

```powershell
python edge_tts.py   "<путь к .md>" [--voice ru-RU-SvetlanaNeural] [--rate +10%]
python silero_tts.py "<путь к .md>"
python kokoro_tts.py "<путь к .md>"
```

Удобно для автоматизации / Shell commands, где меню нежелательно.

### Примеры запуска

#### 1. Авто-режим с меню

```powershell
python tts.py "C:\vault\заметка.md"
```

#### 2. Явно edge, мужской голос, +20%

```powershell
python tts.py "C:\vault\заметка.md" --engine edge --voice ru-RU-DmitryNeural --rate +20%
```

Создаст:

```
заметка.ru.edge.5118fceb47.mp3
заметка.ru.edge.5118fceb47.srt
```

#### 3. Silero офлайн + SRT

```powershell
python tts.py "C:\vault\заметка.md" --engine silero
```

Создаст:

```
заметка.ru.silero.be1d1317f4.wav
заметка.ru.silero.be1d1317f4.srt
```

#### 4. Kokoro, английская заметка, скорость 1.2

```powershell
python tts.py "C:\vault\notes\k8s-networking.md" --engine kokoro --speed 1.2
```

Создаст:

```
k8s-networking.en.kokoro.<hash>.wav
k8s-networking.en.kokoro.<hash>.srt
```

#### 5. Язык не русский и не английский (например, украинский/польский)

Движки **не блокируют** по языку. Можно озвучить любым:

```powershell
python tts.py "C:\vault\нотатка.md" --engine edge --voice uk-UA-OstapNeural
```

edge-tts поддерживает ~100 языков (см. `list_voices()`), silero/kokoro — свои (см. раздел Голоса). Скрипт **не отказывается** синтезировать «не тот» язык — просто звучание может быть с акцентом. Предупреждений больше нет.

#### 6. Озвучить все заметки в папке

```powershell
Get-ChildItem "C:\vault\DevOps" -Recurse -Filter "*.md" | ForEach-Object {
    python tts.py $_.FullName --engine edge
}
```

#### 7. Проверить язык без синтеза

```powershell
python -c "from common import read_note, detect_lang; from pathlib import Path; _, t = read_note(Path(r'C:\vault\заметка.md')); print('lang:', detect_lang(t), '| chars:', len(t))"
```

#### 8. Очистить кэш для заметки

```powershell
Remove-Item "C:\vault\заметка.*.mp3","C:\vault\заметка.*.wav","C:\vault\заметка.*.srt" -ErrorAction SilentlyContinue
```

### Субтитры (SRT) — у всех трёх движков

| Движок   | Гранулярность SRT              | Как используется                                    |
| -------- | ------------------------------ | --------------------------------------------------- |
| `edge`   | по словам                      | Media Extended / VLC / mpv показывают слово-в-слово |
| `silero` | по фрагментам (≤900 символов)  | абзац-в-абзац                                       |
| `kokoro` | по фрагментам (≤1500 символов) | абзац-в-абзац                                       |

Открой `.mp3`/`.wav` в **Media Extended** (Obsidian) или VLC — `.srt` подхватится автоматически (имя совпадает с аудио).

````

---

## Что ещё добавить в README (кратко, вставь в соответствующие разделы)

В **Голоса**:

```markdown
### Любой язык через edge-tts

edge-tts поддерживает ~100 языков и десятки голосов. Полный список:
```powershell
python -c "import asyncio, edge_tts; [print(v['ShortName']) for v in asyncio.run(edge_tts.list_voices())]"
````

Фильтр по локали:

```powershell
# только русские
python -c "import asyncio, edge_tts; [print(v['ShortName']) for v in asyncio.run(edge_tts.list_voices()) if v['Locale'].startswith('ru-')]"
# только украинские
python -c "import asyncio, edge_tts; [print(v['ShortName']) for v in asyncio.run(edge_tts.list_voices()) if v['Locale'].startswith('uk-')]"
```

Примеры голосов не-RU:

- `uk-UA-OstapNeural`, `uk-UA-PolinaNeural` — украинский
- `pl-PL-ZofiaNeural`, `pl-PL-MarekNeural` — польский
- `de-DE-KatjaNeural`, `de-DE-ConradNeural` — немецкий
- `fr-FR-DeniseNeural`, `fr-FR-HenriNeural` — французский
- `en-US-AriaNeural`, `en-US-GuyNeural` — английский (альтернатива Kokoro, если нужен онлайн)

Запуск:

```powershell
python tts.py "C:\vault\нотатка.md" --engine edge --voice uk-UA-OstapNeural
```

````

В **Кэш**:

```markdown
Имя файла: `заметка.<lang>.<engine>.<hash>.<ext>`. `<lang>` — определённый язык
(или `unknown` для коротких/смешанных текстов), `<engine>` — движок, `<hash>` —
md5 от текста+языка+движка. Меняешь движок/язык/текст → новый файл.
````

В **Траблшутинг** добавить:

```markdown
| `espeak-ng-data\phontab: No such file` (Kokoro) | espeakng-loader не нашёл данные | `pip install espeakng-loader`; в `kokoro_tts.py` выставляется `ESPEAK_DATA_PATH` из пакета |
| Меню не появляется, сразу синтез | передан `--engine` | убери `--engine`, чтобы получить меню |
| Язык определился как `cy`/`unknown` | langdetect шумит на коротком/смешанном тексте | не ошибка; выбери движок вручную, синтез не блокируется |
```

---

## Итог изменений

| Файл               | Что поменялось                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------- |
| `common.py`        | `detect_lang` → `unknown` вместо `ru`; `srt_time`, `write_srt`                                          |
| `silero_tts.py`    | убрано предупреждение о языке; SRT по фрагментам                                                        |
| `kokoro_tts.py`    | фикс `ESPEAK_DATA_PATH`; нарезка; SRT; убрано предупреждение                                            |
| `edge_tts.py`      | убрано предупреждение (SRT уже был)                                                                     |
| `tts.py`           | интерактивное меню `choose_engine`; `--speed` для kokoro                                                |
| `requirements.txt` | `espeakng-loader`                                                                                       |
| `README.md`        | раздел «Использование» переписан: меню, все опции, SRT для всех движков, примеры, любой язык через edge |

После этого:

- `python tts.py "note.md"` → меню, без языковых блокировок;
- `python tts.py "note.md" --engine kokoro` → работает на любом тексте (с оговоркой, что Kokoro — EN-модель, но не отказывается);
- каждый движок создаёт `.srt`;
- README описывает все опции и примеры.

Кидай, если хочешь, чтобы я выложил **полные финальные версии** всех пяти файлов одним куском (без «замени фрагмент») — соберу в одном сообщении для копипасты в репо.

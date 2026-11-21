"""Универсальный TTS.

    python tts.py "note.md"                       # интерактивное меню
    python tts.py "note.md" --engine silero       # без меню
    python tts.py "note.md" --engine edge --voice ru-RU-DmitryNeural --rate +15%
"""
import sys
from pathlib import Path

from common import read_note, detect_lang


def choose_engine(lang: str) -> str:
    print("\nВыбери движок:")
    print("  1) edge    — RU/др., онлайн, лучшее качество (Azure Neural)")
    print("  2) silero  — RU, офлайн")
    hint = {"ru": "edge", "en": "kokoro"}.get(lang, "edge")
    print(f"  (язык заметки: {lang}, рекомендуется: {hint})")
    while True:
        ans = input("Номер [1/2] или имя (edge/silero/kokoro), Enter = рекомендованный: ").strip().lower()
        if ans == "":
            return hint
        if ans in ("1", "edge"):
            return "edge"
        if ans in ("2", "silero"):
            return "silero"
        print("Не понял, ещё раз.")


def parse_args(argv):
    path = Path(argv[1])
    engine = None
    voice = None
    rate = "+10%"
    speed = None
    args = argv[2:]
    for i, a in enumerate(args):
        if a == "--engine" and i + 1 < len(args):
            engine = args[i + 1]
        if a == "--voice" and i + 1 < len(args):
            voice = args[i + 1]
        if a == "--rate" and i + 1 < len(args):
            rate = args[i + 1]
        if a == "--speed" and i + 1 < len(args):
            speed = float(args[i + 1])
    return path, engine, voice, rate, speed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path, engine, voice, rate, speed = parse_args(sys.argv)
    if not path.exists():
        print(f"Файл не найден: {path}")
        sys.exit(1)

    try:
        _, text = read_note(path)
    except ValueError as e:
        print(f"Ошибка: {e}")
        sys.exit(2)

    lang = detect_lang(text)

    if engine is None:
        engine = choose_engine(lang)

    print(f"Язык: {lang}, движок: {engine}")

    if engine == "silero":
        from silero_synth import tts_file
        out = tts_file(path)
    elif engine == "edge":
        from edge_synth import tts_file as edge_tts_file
        out = edge_tts_file(path, voice=voice or "ru-RU-SvetlanaNeural", rate=rate)
    else:
        print(f"Неизвестный движок: {engine}")
        sys.exit(1)

    print(f"OK: {out}")


if __name__ == "__main__":
    main()
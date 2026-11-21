"""
Установка моделей и зависимостей для Silero + edge-tts.

Запуск:
    python install_models.py

Что делает:
  1. Проверяет Python-пакеты (langdetect, numpy, soundfile, torch, silero, edge-tts).
     Отсутствующие — ставит через pip.
  2. Скачивает models/v4_ru.pt (Silero RU), если его нет или размер битый.
  3. Проверяет, что edge-tts доступен в сети (list_voices).
  4. Печатает итог.

Идемпотентен: повторный запуск ничего не ломает.
"""
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
MODELS = BASE / "models"
MODELS.mkdir(exist_ok=True)

SILERO_URL = "https://models.silero.ai/models/tts/ru/v4_ru.pt"
SILERO_PATH = MODELS / "v4_ru.pt"
SILERO_MIN_SIZE = 30 * 1024 * 1024   # 30 МБ — ниже считаем битым (норма ~38 МБ)
SILERO_MAX_SIZE = 60 * 1024 * 1024

PACKAGES = [
    "langdetect>=1.0.9",
    "numpy>=1.24",
    "soundfile>=0.12",
    "torch>=2.0",
    "silero>=0.5.5",
    "edge-tts>=7.0",
]


def run(cmd):
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def ensure_packages():
    print("\n=== Проверка Python-пакетов ===")
    missing = []
    for pkg in PACKAGES:
        name = pkg.split(">=")[0].split("==")[0]
        code = subprocess.call(
            [sys.executable, "-c", f"import {name.replace('-', '_')}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if code != 0:
            missing.append(pkg)
            print(f"  [нет] {pkg}")
        else:
            print(f"  [ok ] {pkg}")

    if missing:
        print(f"\nСтавлю отсутствующие: {', '.join(missing)}")
        rc = run([sys.executable, "-m", "pip", "install", "--upgrade", *missing])
        if rc != 0:
            print("ОШИБКА: pip install завершился с ошибкой.")
            print("Попробуй вручную:")
            print(f"  {sys.executable} -m pip install {' '.join(missing)}")
            sys.exit(1)
    else:
        print("Все пакеты уже установлены.")


def download_with_progress(url: str, dst: Path):
    print(f"\nСкачиваю: {url}")
    print(f"       -> {dst}")

    def hook(blocks, block_size, total_size):
        if total_size > 0:
            downloaded = blocks * block_size
            pct = min(downloaded * 100 / total_size, 100)
            mb_done = downloaded / 1024 / 1024
            mb_total = total_size / 1024 / 1024
            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)
            sys.stdout.write(f"\r  [{bar}] {pct:5.1f}%  {mb_done:5.1f}/{mb_total:.1f} МБ")
            sys.stdout.flush()
        else:
            sys.stdout.write(f"\r  скачано: {blocks * block_size / 1024 / 1024:.1f} МБ")
            sys.stdout.flush()

    tmp = dst.with_suffix(dst.suffix + ".part")
    try:
        urllib.request.urlretrieve(url, tmp, reporthook=hook)
        print()
        tmp.replace(dst)
    except Exception as e:
        print(f"\nОШИБКА скачивания: {e}")
        if tmp.exists():
            tmp.unlink()
        raise


def ensure_silero():
    print("\n=== Модель Silero RU (v4_ru.pt) ===")
    if SILERO_PATH.exists():
        size = SILERO_PATH.stat().st_size
        if SILERO_MIN_SIZE <= size <= SILERO_MAX_SIZE:
            print(f"  [ok ] {SILERO_PATH.name} — {size/1024/1024:.1f} МБ")
            return
        print(f"  [!!] {SILERO_PATH.name} весит {size/1024/1024:.1f} МБ — битый, перекачиваю")
        SILERO_PATH.unlink()
    else:
        print(f"  [нет] {SILERO_PATH.name} — качаю")

    download_with_progress(SILERO_URL, SILERO_PATH)

    size = SILERO_PATH.stat().st_size
    if not (SILERO_MIN_SIZE <= size <= SILERO_MAX_SIZE):
        print(f"ОШИБКА: после скачивания размер {size/1024/1024:.1f} МБ "
              f"вне диапазона [{SILERO_MIN_SIZE/1024/1024:.0f}, "
              f"{SILERO_MAX_SIZE/1024/1024:.0f}] МБ. Перекачай вручную:")
        print(f'  curl.exe -L "{SILERO_URL}" -o "{SILERO_PATH}"')
        sys.exit(1)
    print(f"  [ok ] {SILERO_PATH.name} — {size/1024/1024:.1f} МБ")


def ensure_edge_works():
    print("\n=== Проверка edge-tts (сеть до Microsoft) ===")
    code = subprocess.call([
        sys.executable, "-c",
        "import asyncio, edge_tts; "
        "vs=asyncio.run(edge_tts.list_voices()); "
        "ru=[v['ShortName'] for v in vs if v['Locale'].startswith('ru-')]; "
        "print('  RU голоса:', ', '.join(ru)) if ru else print('  ВНИМАНИЕ: RU голосов нет')"
    ])
    if code != 0:
        print("  ОШИБКА: edge-tts не смог получить список голосов.")
        print("  Проверь интернет и доступ к speech.platform.bing.com:443")
        print("  Модели при этом скачаны, edge-tts будет работать, когда сеть починится.")
    else:
        print("  [ok ] edge-tts доступен")


def summary():
    print("\n=== Итог ===")
    print(f"  models/v4_ru.pt: {'есть' if SILERO_PATH.exists() else 'НЕТ'}")
    print(f"  edge-tts: работает через сеть, моделей не требует")
    print("\nГотово. Запускай:")
    print(f'  {sys.executable} tts.py "C:\\путь\\к\\заметке.md" --engine silero')
    print(f'  {sys.executable} tts.py "C:\\путь\\к\\заметке.md" --engine edge')


def main():
    print("Установка моделей для Silero + edge-tts")
    print(f"Проект: {BASE}")
    print(f"Python: {sys.executable}")
    ensure_packages()
    ensure_silero()
    ensure_edge_works()
    summary()


if __name__ == "__main__":
    main()
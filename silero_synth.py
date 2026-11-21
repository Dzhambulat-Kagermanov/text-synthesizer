import sys
import re
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from torch.package import PackageImporter

from common import MODELS, read_note, split_text, detect_lang, cache_path, write_srt

_silero = None

# Пауза между предложениями (сек)
SENTENCE_PAUSE = 0.30
# Минимальная длина предложения, чтобы синтезировать отдельно
MIN_SENT_CHARS = 8
# Максимальная длина предложения; длиннее — режем по запятым
MAX_SENT_CHARS = 220


def _ascii_copy(src: Path) -> Path:
    tmp_dir = Path("C:/Temp/silero_tts_local")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dst = tmp_dir / "v4_ru.pt"
    if (not dst.exists()) or (dst.stat().st_size != src.stat().st_size):
        shutil.copy2(src, dst)
    return dst


def get_silero():
    global _silero
    if _silero is None:
        torch.set_num_threads(4)
        model_path = MODELS / "v4_ru.pt"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Нет файла модели: {model_path}\n"
                f'Скачай: curl.exe -L "https://models.silero.ai/models/tts/ru/v4_ru.pt" '
                f'-o "models\\v4_ru.pt"'
            )
        load_path = _ascii_copy(model_path)
        imp = PackageImporter(str(load_path))
        _silero = imp.load_pickle("tts_models", "model")
        _silero.to(torch.device("cpu"))
    return _silero


def _split_into_sentences(text: str):
    """
    Делит текст на предложения, пригодные для отдельного синтеза.
    Длинные предложения (> MAX_SENT_CHARS) режет по запятым/точкам с запятой.
    Слишком короткие (< MIN_SENT_CHARS) — приклеивает к предыдущему.
    """
    raw_parts = re.split(r"(?<=[.!?…])\s+", text.strip())
    result = []
    for p in raw_parts:
        p = p.strip()
        if not p:
            continue
        if len(p) > MAX_SENT_CHARS:
            # режем по запятым/точкам с запятой/двоеточиям
            subs = re.split(r"(?<=[,;:])\s+", p)
            for s in subs:
                s = s.strip()
                if s:
                    result.append(s)
        else:
            result.append(p)

    # склеиваем слишком короткие с предыдущим
    merged = []
    for s in result:
        if merged and len(s) < MIN_SENT_CHARS:
            merged[-1] = merged[-1] + " " + s
        else:
            merged.append(s)
    return merged


def synth(text: str, out: Path, speaker="baya", sample_rate=48000):
    model = get_silero()

    sentences = _split_into_sentences(text)
    if not sentences:
        raise ValueError("Не удалось разбить текст на предложения")

    print(f"Silero: {len(sentences)} предложений, всего {len(text)} символов")

    audios = []
    srt_entries = []
    t_cursor = 0.0
    skipped = 0
    for i, sent in enumerate(sentences, 1):
        if len(sent) < 3 or not re.search(r"[А-Яа-яЁё]", sent):
            print(f"  [{i}/{len(sentences)}] пропуск (нет кириллицы): {sent[:40]!r}")
            skipped += 1
            continue
        print(f"  [{i}/{len(sentences)}] {len(sent)} символов...")
        try:
            audio = model.apply_tts(
                text=sent, speaker=speaker, sample_rate=sample_rate,
                put_accent=True, put_yo=True,
            )
        except Exception as e:
            msg = str(e).strip() or type(e).__name__
            print(f"  [{i}/{len(sentences)}] Silero не осилил ({msg}); пропуск")
            skipped += 1
            continue

        arr = audio.numpy()
        dur = len(arr) / sample_rate

        # SRT: точное окно для этого предложения
        srt_entries.append((t_cursor, t_cursor + dur, sent))

        audios.append(arr)
        # пауза между предложениями
        audios.append(np.zeros(int(sample_rate * SENTENCE_PAUSE), dtype=arr.dtype))
        t_cursor += dur + SENTENCE_PAUSE

    if not audios:
        raise RuntimeError(
            f"Silero не смог синтезировать ни одного предложения "
            f"(пропущено {skipped}/{len(sentences)}). "
            f"Скорее всего в тексте нет русских слов."
        )

    full = np.concatenate(audios[:-1])
    sf.write(out, full, sample_rate)

    srt_path = out.with_suffix(".srt")
    if write_srt(srt_path, srt_entries):
        print(f"SRT: {srt_path} ({len(srt_entries)} предложений, "
              f"~{t_cursor/60:.1f} мин аудио)")


def tts_file(md_path: Path, speaker="baya") -> Path:
    _, text = read_note(md_path)

    if not re.search(r"[А-Яа-яЁё]", text):
        raise ValueError(
            "В тексте нет кириллицы. Silero RU модель озвучивает только русский. "
            "Для английского: --engine kokoro. Для любого: --engine edge."
        )

    lang = detect_lang(text)
    out = cache_path(md_path, lang, "silero", "wav", text)
    srt = out.with_suffix(".srt")
    if out.exists() and out.stat().st_size > 0 and srt.exists() and srt.stat().st_size > 0:
        return out
    synth(text, out, speaker=speaker)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python silero_synth.py <путь к .md>")
        sys.exit(1)
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"Файл не найден: {p}")
        sys.exit(1)
    print(f"OK: {tts_file(p)}")
import sys
import asyncio
from pathlib import Path

import edge_tts

from common import read_note, split_text, detect_lang, cache_path, write_srt


MP3_BITRATE = 48_000  # edge-tts отдаёт CBR 48 kbps


async def _synth_chunk(chunk: str, voice: str, rate: str, volume: str, part: Path):
    """Синтез одного куска. Возвращает список WordBoundary: [(offset, duration, text)]."""
    comm = edge_tts.Communicate(
        chunk, voice, rate=rate, volume=volume, boundary="WordBoundary"
    )
    got = False
    boundaries = []
    with open(part, "wb") as f:
        async for ev in comm.stream():
            if ev["type"] == "audio":
                f.write(ev["data"])
                got = True
            elif ev["type"] == "WordBoundary":
                boundaries.append((
                    ev["offset"] / 10_000_000,
                    ev["duration"] / 10_000_000,
                    ev["text"],
                ))
    if not got or part.stat().st_size < 2000:
        raise RuntimeError(
            f"edge-tts вернул пустой поток "
            f"({part.stat().st_size if part.exists() else 0} байт)"
        )
    return boundaries


async def _synth_all(chunks, voice, rate, volume, tmp_dir, concurrency=4):
    sem = asyncio.Semaphore(concurrency)

    async def _guarded(i, chunk):
        async with sem:
            part = tmp_dir / f"part_{i:03d}.mp3"
            for attempt in range(1, 4):
                try:
                    if part.exists():
                        part.unlink()
                    bounds = await _synth_chunk(chunk, voice, rate, volume, part)
                    print(f"  [{i}/{len(chunks)}] ok, {part.stat().st_size} байт, "
                          f"{len(bounds)} слов")
                    return part, bounds
                except Exception as e:
                    print(f"  [{i}] попытка {attempt}: {e}")
                    await asyncio.sleep(2 * attempt)
            raise RuntimeError(f"фрагмент {i} не удался после 3 попыток")

    return await asyncio.gather(*[_guarded(i, c) for i, c in enumerate(chunks, 1)])


def _group_words_into_phrases(
    words,
    max_words: int = 10,
    max_chars: int = 80,
    max_gap: float = 0.4,
    max_duration: float = 6.0,
):
    """
    Группирует [(start, end, text), ...] в фразы для SRT.

    Новая фраза начинается, если:
      - пауза между словами > max_gap секунд, ИЛИ
      - в текущей фразе уже >= max_words слов, ИЛИ
      - длина фразы с новым словом > max_chars символов, ИЛИ
      - длительность фразы с новым словом > max_duration секунд.
    """
    if not words:
        return []

    phrases = []
    cur_start, cur_end, cur_text = words[0][0], words[0][1], [words[0][2]]
    prev_end = words[0][1]

    for start, end, txt in words[1:]:
        gap = start - prev_end
        projected_text = " ".join(cur_text + [txt])
        projected_dur = end - cur_start

        new_phrase = (
            gap > max_gap
            or len(cur_text) >= max_words
            or len(projected_text) > max_chars
            or projected_dur > max_duration
        )

        if new_phrase:
            phrases.append((cur_start, cur_end, " ".join(cur_text)))
            cur_start, cur_end, cur_text = start, end, [txt]
        else:
            cur_text.append(txt)
            cur_end = end
        prev_end = end

    phrases.append((cur_start, cur_end, " ".join(cur_text)))
    return phrases


def synth(text: str, out: Path, voice="ru-RU-SvetlanaNeural",
          rate="+10%", volume="+0%", max_len=2000, concurrency=4):
    chunks = split_text(text, max_len=max_len)
    if not chunks:
        raise ValueError("Пустой текст после нарезки")

    print(f"edge-tts: {len(chunks)} фрагмент(ов), всего {len(text)} символов")

    tmp_dir = out.parent / "_edge_tmp"
    tmp_dir.mkdir(exist_ok=True)

    results = asyncio.run(_synth_all(chunks, voice, rate, volume, tmp_dir, concurrency))

    # Склейка mp3 + сбор абсолютных таймингов слов
    all_words = []
    time_offset = 0.0
    total = 0
    with open(out, "wb") as f:
        for part, bounds in results:
            data = part.read_bytes()
            f.write(data)
            total += len(data)
            duration = len(data) * 8 / MP3_BITRATE
            for offset, dur, txt in bounds:
                start = time_offset + offset
                end = start + dur
                all_words.append((start, end, txt))
            time_offset += duration

    if total == 0:
        raise RuntimeError("Итоговый mp3 пустой")

    print(f"edge-tts: итог {total/1024/1024:.1f} МБ, ~{time_offset/60:.1f} мин, "
          f"{len(all_words)} слов")

    # Группируем слова в читаемые фразы
    srt_entries = _group_words_into_phrases(
        all_words, max_words=10, max_chars=80, max_gap=0.4, max_duration=6.0
    )

    srt_path = out.with_suffix(".srt")
    if write_srt(srt_path, srt_entries):
        print(f"SRT: {srt_path} ({len(srt_entries)} фраз)")
    else:
        print("ВНИМАНИЕ: edge-tts не вернул WordBoundary, SRT не создан")
        if srt_path.exists():
            srt_path.unlink()

    for part, _ in results:
        try:
            part.unlink()
        except OSError:
            pass
    try:
        tmp_dir.rmdir()
    except OSError:
        pass


def tts_file(md_path: Path, voice="ru-RU-SvetlanaNeural", rate="+10%") -> Path:
    _, text = read_note(md_path)
    lang = detect_lang(text)
    out = cache_path(md_path, lang, "edge", "mp3", text)
    srt = out.with_suffix(".srt")
    if out.exists() and out.stat().st_size > 0 and srt.exists() and srt.stat().st_size > 0:
        return out
    if srt.exists() and srt.stat().st_size == 0:
        srt.unlink()
    synth(text, out, voice=voice, rate=rate)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python edge_synth.py <путь к .md> [--voice ...] [--rate +10%]")
        sys.exit(1)
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"Файл не найден: {p}")
        sys.exit(1)
    voice = "ru-RU-SvetlanaNeural"
    rate = "+10%"
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--voice" and i + 1 < len(args):
            voice = args[i + 1]
        if a == "--rate" and i + 1 < len(args):
            rate = args[i + 1]
    print(f"OK: {tts_file(p, voice=voice, rate=rate)}")
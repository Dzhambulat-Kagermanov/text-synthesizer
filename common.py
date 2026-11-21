import re
import hashlib
from pathlib import Path
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

BASE = Path(__file__).parent
MODELS = BASE / "models"
CACHE = BASE / "cache"
CACHE.mkdir(exist_ok=True)

MIN_CHARS = 20


def clean_md(md: str) -> str:
    md = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.S)
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"`[^`]*`", "", md)
    md = re.sub(r"!\[.*?\]\(.*?\)", "", md)
    md = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", md)
    md = re.sub(r"^#{1,6}\s*", "", md, flags=re.M)
    md = re.sub(r"[*_~>|-]{1,}", " ", md)
    md = re.sub(r"\n{2,}", "\n\n", md)
    return md.strip()


def split_text(text: str, max_len: int = 900) -> list:
    text = text.strip()
    if len(text) <= max_len:
        return [text] if text else []

    chunks = []
    paragraphs = re.split(r"\n\s*\n", text)
    buf = ""
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(p) > max_len:
            for s in re.split(r"(?<=[.!?…])\s+", p):
                if len(buf) + len(s) + 1 <= max_len:
                    buf = f"{buf} {s}".strip()
                else:
                    if buf:
                        chunks.append(buf)
                    if len(s) > max_len:
                        wbuf = ""
                        for w in s.split():
                            if len(wbuf) + len(w) + 1 <= max_len:
                                wbuf = f"{wbuf} {w}".strip()
                            else:
                                if wbuf:
                                    chunks.append(wbuf)
                                wbuf = w
                        buf = wbuf
                    else:
                        buf = s
        else:
            if len(buf) + len(p) + 2 <= max_len:
                buf = f"{buf}\n\n{p}".strip()
            else:
                if buf:
                    chunks.append(buf)
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


def detect_lang(text: str) -> str:
    t = text.strip()
    if len(t) < 20:
        return "unknown"
    try:
        return detect(t)
    except Exception:
        return "unknown"


def is_speakable(text: str) -> bool:
    return len(re.findall(r"[A-Za-zА-Яа-яЁё]", text)) >= 3


def cache_path(md_path: Path, lang: str, engine: str, ext: str, text: str) -> Path:
    h = hashlib.md5((text + lang + engine).encode()).hexdigest()[:10]
    return md_path.parent / f"{md_path.stem}.{lang}.{engine}.{h}.{ext}"


def read_note(md_path: Path):
    raw = md_path.read_text(encoding="utf-8")
    text = clean_md(raw)
    if not text:
        raise ValueError("Пустой текст после чистки markdown")
    if len(text) < MIN_CHARS:
        raise ValueError(
            f"Слишком короткий текст ({len(text)} символов, минимум {MIN_CHARS}). "
            f"TTS на таком часто падает — добавь текста."
        )
    if not is_speakable(text):
        raise ValueError(f"В тексте нет букв (только цифры/символы): {text!r}")
    return raw, text


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(path: Path, entries) -> bool:
    """entries: [(start_sec, end_sec, text), ...]. Возвращает True, если что-то записано."""
    if not entries:
        return False
    with open(path, "w", encoding="utf-8") as f:
        for idx, (start, end, txt) in enumerate(entries, 1):
            f.write(f"{idx}\n{srt_time(start)} --> {srt_time(end)}\n{txt}\n\n")
    return True
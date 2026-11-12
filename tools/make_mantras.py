"""Make mantra recordings with a natural neural female voice, a tanpura drone, temple bells and reverb.

Needs: pip install edge-tts numpy miniaudio lameenc truststore
Usage: python tools/make_mantras.py [--voice mr-IN-AarohiNeural] [--only gayatri,ganesha]
Writes audio/<id>.mp3 and audio/marks.json (start time of every line, so the dashboard highlights in sync).
The mantra texts are read from src/dashboard.html, so the recordings always match the screen.
"""
import argparse
import asyncio
import json
import re
from pathlib import Path

try:  # use the Windows certificate store (needed behind antivirus TLS inspection)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import edge_tts
import lameenc
import miniaudio
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audio"
SR = 24000


def load_mantras():
    js = (ROOT / "src" / "dashboard.html").read_text(encoding="utf-8")
    block = js[js.index("const MANTRAS = {"): js.index("const QUOTES")]
    out = []
    for m in re.finditer(r"\{ id: '(\w+)'.*?reps: (\d+),\s*lines: \[(.*?)\]\],", block, re.S):
        lines = re.findall(r"\['([^']*)', '[^']*'\]", m.group(3) + "]")
        out.append({"id": m.group(1), "reps": int(m.group(2)), "lines": lines})
    return out


def clean(line):
    """Devanagari for the voice: drop dandas so it doesn't pause oddly, keep the words."""
    return re.sub(r"[।॥|]", "", line).strip()


async def tts(text, voice, rate, pitch):
    buf = bytearray()
    async for chunk in edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).stream():
        if chunk["type"] == "audio":
            buf += chunk["data"]
    pcm = miniaudio.decode(bytes(buf), output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=SR)
    a = np.frombuffer(pcm.samples, dtype=np.float32).copy()
    nz = np.flatnonzero(np.abs(a) > 0.01)  # trim the silence edge-tts adds
    return a[max(0, nz[0] - 600): nz[-1] + 2400] if len(nz) else a


def tanpura(seconds, tonic):
    """Plucked Pa-Sa-Sa-Sa cycle with rich harmonics and slow decay: a soft tanpura bed."""
    n = int(seconds * SR)
    out = np.zeros(n + SR * 4, dtype=np.float32)
    t = np.arange(int(SR * 3.6)) / SR
    pattern = [tonic * 1.5 / 2, tonic, tonic, tonic / 2]
    k, step = 0, 0.62
    while k * step * SR < n:
        f = pattern[k % 4]
        tone = sum((0.9 ** h) * np.sin(2 * np.pi * f * h * t * (1 + 0.0007 * h)) for h in range(1, 14))
        env = np.exp(-t / 1.4) * (1 - np.exp(-t / 0.01))
        s = int(k * step * SR)
        out[s:s + len(t)] += (tone * env).astype(np.float32)
        k += 1
    out = out[:n]
    fade = int(SR * 1.5)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.abs(out).max() + 1e-9)


def bell(f=880.0, seconds=4.0):
    t = np.arange(int(SR * seconds)) / SR
    partials = [(1, 1, 2.6), (2.76, 0.5, 1.3), (5.40, 0.25, 0.7), (8.93, 0.12, 0.4), (0.5, 0.3, 3.0)]
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in partials)
    return (s / np.abs(s).max()).astype(np.float32)


def reverb(x, seconds=1.9, wet=0.22):
    rng = np.random.default_rng(7)
    n = int(SR * seconds)
    ir = rng.standard_normal(n).astype(np.float32) * np.exp(-np.arange(n) / SR * 6.9 / seconds)
    ir[: int(SR * 0.02)] = 0  # pre-delay
    ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:L]
    dry = np.concatenate([x, np.zeros(n, dtype=np.float32)])
    return (dry * (1 - wet) + y * wet * 1.4).astype(np.float32)


def to_mp3(x, path):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()
    enc = lameenc.Encoder()
    enc.set_bit_rate(64); enc.set_in_sample_rate(SR); enc.set_channels(1); enc.set_quality(2)
    path.write_bytes(enc.encode(pcm) + enc.flush())


async def make(m, voice, rate, pitch, tonic):
    voiced = [await tts(clean(l), voice, rate, pitch) for l in m["lines"]]
    gap, round_gap, lead = 0.85, 1.8, 2.6
    parts, marks, t = [np.zeros(int(SR * lead), np.float32)], [], lead
    for r in range(m["reps"]):
        for i, v in enumerate(voiced):
            marks.append(round(t, 2))
            parts += [v, np.zeros(int(SR * gap), np.float32)]
            t += len(v) / SR + gap
        if r < m["reps"] - 1:
            parts.append(np.zeros(int(SR * round_gap), np.float32)); t += round_gap
    parts.append(np.zeros(int(SR * 3.5), np.float32))
    vox = np.concatenate(parts)
    vox = vox / (np.abs(vox).max() + 1e-9) * 0.85
    mix = reverb(vox)
    mix[: len(mix)] += 0.10 * tanpura(len(mix) / SR, tonic)[: len(mix)]
    b = bell()
    mix[int(SR * 0.3): int(SR * 0.3) + len(b)] += 0.28 * b
    end = int(SR * t)
    mix[end: end + len(b)] += 0.28 * b[: len(mix) - end]
    mix = mix / np.abs(mix).max() * 0.9
    return mix, marks, round(len(mix) / SR, 2)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="mr-IN-AarohiNeural")  # family's pick; alternative: hi-IN-SwaraNeural
    ap.add_argument("--rate", default="-22%")
    ap.add_argument("--pitch", default="-6Hz")
    ap.add_argument("--tonic", type=float, default=138.6)  # C#3, sits under a female voice
    ap.add_argument("--only", default="")
    ap.add_argument("--suffix", default="")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    marks_file = OUT / "marks.json"
    all_marks = json.loads(marks_file.read_text()) if marks_file.exists() else {}
    for m in load_mantras():
        if a.only and m["id"] not in a.only.split(","):
            continue
        mix, marks, dur = await make(m, a.voice, a.rate, a.pitch, a.tonic)
        f = OUT / f"{m['id']}{a.suffix}.mp3"
        to_mp3(mix, f)
        if not a.suffix:
            all_marks[m["id"]] = {"marks": marks, "duration": dur}
        print(f"{f.name:28} {dur:6.1f} s  {f.stat().st_size // 1024} KB  {len(marks)} lines")
    marks_file.write_text(json.dumps(all_marks, indent=1))


if __name__ == "__main__":
    asyncio.run(main())

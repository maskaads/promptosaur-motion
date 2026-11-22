#!/usr/bin/env python3
"""Word timestamps for a voice-over whose text you already have.

Speech-to-text tools (Whisper and friends) guess where a word starts and are
often 3 to 20 frames off, worst on numbers. This script does forced
alignment instead: an acoustic model (wav2vec2, CTC) is told the exact text
and finds where each letter sounds. Word starts land within a frame or two.

  1. Your script text is turned into the words that are actually spoken:
     "145" -> "one hundred forty five", "$5" -> "five dollars", "T." -> "T".
     Fix any reading with --say, e.g. --say "2026=twenty twenty six".
  2. The audio runs through the model in 30 s windows (any length works).
  3. A Viterbi pass fits your letters to the audio.
  4. Every start moves 0.04 s earlier (--lead): the model hears a word
     1 to 2 frames after it begins. Tested against the word events of two
     Windows voices: with the shift 38 of 55 and 24 of 27 words landed
     within 1 frame, 52 of 55 and 27 of 27 within 2. A Whisper transcript
     of the same audio got 13 of 55 within 1 frame and was up to 20 frames
     off on "million" after a number.
  5. timing.json gets every word of your script with seconds and the frame
     number, plus a list of numbers to check in the render.

Usage:
  python align.py voice.mp3 voice.txt [--fps 30] [--out timing.json]
                  [--say "TEXT=spoken words"]... [--model facebook/wav2vec2-base-960h]

Needs: pip install torch transformers numpy, and ffmpeg on PATH.
The default model is English. For another language pass a wav2vec2 CTC model
for it (search "wav2vec2 <language>" on Hugging Face) and write numbers in
the script as words.

The frame of a word is round(start * fps): the frame closest to the moment
the word begins. Put the visual change on that frame.
"""
import argparse
import json
import re
import subprocess
import sys

import numpy as np

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
SCALES = [(10**12, "trillion"), (10**9, "billion"), (10**6, "million"), (1000, "thousand"), (100, "hundred")]


def int_words(n):
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    for val, name in SCALES:
        if n >= val:
            out = int_words(n // val) + [name]
            return out + (int_words(n % val) if n % val else [])
    return []


def number_words(tok):
    """'145' -> one hundred forty five; '3.5' -> three point five; '1,200' -> ..."""
    tok = tok.replace(",", "")
    if re.fullmatch(r"\d+", tok):
        return int_words(int(tok))
    if re.fullmatch(r"\d+\.\d+", tok):
        a, b = tok.split(".")
        return int_words(int(a)) + ["point"] + [ONES[int(d)] for d in b]
    m = re.fullmatch(r"(\d+)(st|nd|rd|th)", tok)
    if m:
        return int_words(int(m.group(1)))  # close enough for alignment
    return None


def spoken(word, say):
    """Turn one written word into the list of words a speaker says."""
    key = word.strip()
    if key in say:
        return say[key].split()
    w = key.strip("\"'“”‘’()[]{}:;,!?…")
    if w.endswith(".") and not re.fullmatch(r"\d+\.\d+", w):
        w = w[:-1]
    if w in say:
        return say[w].split()
    pre, post = [], []
    if w.startswith("$"):
        w, post = w[1:], ["dollars"]
    if w.endswith("%"):
        w, post = w[:-1], ["percent"] + post
    nums = number_words(w)
    if nums is not None:
        return pre + nums + post
    parts = [p for p in re.split("[-\u2013\u2014/]", w) if p]
    out = []
    for p in parts:
        n = number_words(p)
        out += n if n is not None else [re.sub(r"[^A-Za-z']", "", p)]
    return [o for o in pre + out + post if o]


def load_audio(path, sr=16000):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        capture_output=True, check=True, **({"creationflags": 0x08000000} if sys.platform == "win32" else {})).stdout
    return np.frombuffer(raw, dtype=np.float32).copy(), sr


def emissions(audio, sr, model_name):
    import torch
    from transformers import AutoProcessor, Wav2Vec2ForCTC

    proc = AutoProcessor.from_pretrained(model_name)
    model = Wav2Vec2ForCTC.from_pretrained(model_name).eval()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(dev)
    win, pad = 30 * sr, 2 * sr
    chunks = []
    for s in range(0, len(audio), win):
        a0, a1 = max(0, s - pad), min(len(audio), s + win + pad)
        x = proc(audio[a0:a1], sampling_rate=sr, return_tensors="pt").input_values.to(dev)
        with torch.inference_mode():
            lp = torch.log_softmax(model(x).logits[0], dim=-1).cpu().numpy()
        step = (a1 - a0) / lp.shape[0]  # samples per output frame
        keep0 = int(round((s - a0) / step))
        keep1 = int(round((min(len(audio), s + win) - a0) / step))
        chunks.append(lp[keep0:keep1])
    em = np.concatenate(chunks)
    vocab = proc.tokenizer.get_vocab()
    blank = proc.tokenizer.pad_token_id
    sep = vocab.get("|", vocab.get(" "))
    return em, vocab, blank, sep, len(audio) / sr / em.shape[0]


def viterbi(em, tokens, blank):
    """Fit the token sequence to the emissions. Returns the first frame of each token."""
    T, N = em.shape[0], len(tokens)
    if N > T:
        sys.exit(f"text too long for the audio: {N} letters, {T} audio frames")
    tok = np.array(tokens)
    score = np.full(N, -np.inf)
    back = np.zeros((T, N), dtype=bool)  # True: moved to this token at frame t
    score[0] = em[0, tok[0]]
    lead = em[0, blank]  # leading silence before the first token
    for t in range(1, T):
        e = em[t]
        stay = score + np.maximum(e[blank], e[tok])
        move = np.full(N, -np.inf)
        move[1:] = score[:-1] + e[tok[1:]]
        move[0] = lead + e[tok[0]]
        back[t] = move > stay
        score = np.where(back[t], move, stay)
        lead = lead + e[blank]
    starts = np.zeros(N, dtype=int)
    j = N - 1
    for t in range(T - 1, -1, -1):
        if back[t, j] or t == 0:
            starts[j] = t
            if j == 0:
                break
            j -= 1
    return starts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("text")
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--out", default="timing.json")
    ap.add_argument("--model", default="facebook/wav2vec2-base-960h")
    ap.add_argument("--lead", type=float, default=0.04,
                    help="seconds taken off every start (default 0.04: the model runs 1 to 2 frames late)")
    ap.add_argument("--say", action="append", default=[], help='how a word is read: "2026=twenty twenty six"')
    a = ap.parse_args()

    say = dict(s.split("=", 1) for s in a.say)
    script_words = open(a.text, encoding="utf-8").read().split()
    audio, sr = load_audio(a.audio)
    em, vocab, blank, sep, sec_per_frame = emissions(audio, sr, a.model)
    upper = all(k.upper() == k for k in vocab if k.isalpha())

    tokens, first_tok, readings = [], [], []
    for w in script_words:
        words = spoken(w, say)
        readings.append(" ".join(words))
        first_tok.append(len(tokens) if words else None)
        for k, sw in enumerate(words):
            if tokens and sep is not None:
                tokens.append(sep)
                if k == 0 and first_tok[-1] is not None:
                    first_tok[-1] = len(tokens)
            for ch in (sw.upper() if upper else sw.lower()):
                if ch in vocab:
                    tokens.append(vocab[ch])
    starts = viterbi(em, tokens, blank)

    words = []
    for i, w in enumerate(script_words):
        ti = first_tok[i]
        nxt = next((first_tok[k] for k in range(i + 1, len(script_words)) if first_tok[k] is not None), None)
        if ti is None:
            continue
        t0 = max(0.0, starts[ti] * sec_per_frame - a.lead)
        t1 = (starts[nxt - 1] if nxt else em.shape[0]) * sec_per_frame  # up to the gap before the next word
        words.append(dict(i=i, word=w, spoken=readings[i], start=round(t0, 3), end=round(t1, 3),
                          frame=int(round(t0 * a.fps)), end_frame=int(round(t1 * a.fps)),
                          number=bool(re.search(r"\d", w))))

    json.dump(dict(audio=a.audio, fps=a.fps, words=words), open(a.out, "w", encoding="utf-8"), indent=1)
    print(f"{len(words)} words aligned -> {a.out}")
    nums = [w for w in words if w["number"]]
    if nums:
        print("numbers: check the frame of each one in the render")
        for w in nums:
            print(f"  frame {w['frame']:>5}  {w['start']:7.3f}s  {w['word']}  (read as: {w['spoken']})")


if __name__ == "__main__":
    main()

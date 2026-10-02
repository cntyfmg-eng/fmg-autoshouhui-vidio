"""Synthesize a gentle royalty-free background music bed (numpy, no external assets).

Calm children's-story feel: warm sustained pad + soft pentatonic bell melody +
rounded bass. Key of C major pentatonic, ~68 BPM, loop-friendly, fades in/out.
"""
import numpy as np
import os
import wave

SR = 44100
DUR = 124.8
BPM = 68.0
BEAT = 60.0 / BPM

from config import WORK, ensure_dirs
ensure_dirs()
OUT = str(WORK / "bgm.wav")

n = int(SR * DUR)
t = np.arange(n) / SR

rng = np.random.default_rng(20261002)


def adsr(length, attack, decay, sustain_level, release):
    """Classic ADSR envelope for a given note length in samples."""
    a = int(SR * attack)
    d = int(SR * decay)
    r = int(SR * release)
    s = max(0, length - a - d - r)
    env = np.concatenate([
        np.linspace(0, 1, a, endpoint=False) if a > 0 else np.array([]),
        np.linspace(1, sustain_level, d, endpoint=False) if d > 0 else np.array([]),
        np.full(s, sustain_level),
        np.linspace(sustain_level, 0, r) if r > 0 else np.array([]),
    ])
    if len(env) < length:
        env = np.pad(env, (0, length - len(env)))
    return env[:length]


def place(buf, x, start_sec, gain=1.0):
    """Add signal x into buf at start_sec with gain."""
    i = int(start_sec * SR)
    j = min(len(buf), i + len(x))
    if i < len(buf):
        buf[i:j] += x[: j - i] * gain


def place_at(buf, x, start_sec, gain=1.0):
    """Place a finite-length signal, clipping to the buffer bounds."""
    i = int(start_sec * SR)
    if i >= len(buf):
        return
    seg = x[: len(buf) - i]
    buf[i:i + len(seg)] += seg * gain


def bell(freq, length, amp=0.3, bright=0.5):
    """Soft struck-bell / music-box timbre: fundamental + soft harmonics."""
    tt = np.arange(int(SR * length)) / SR
    sig = np.zeros_like(tt)
    for k, g in enumerate([1.0, 0.45 * bright, 0.22 * bright, 0.10 * bright], start=1):
        if freq * k < SR * 0.45:
            sig += g * np.sin(2 * np.pi * freq * k * tt)
    env = np.exp(-tt * 3.1)            # quick, soft decay
    atk = np.clip(tt / 0.006, 0, 1)   # tiny attack to avoid clicks
    return sig * env * atk * amp / 1.77


def pad_chord(freqs, length, amp=0.10):
    """Warm sustained chord with slow swell and gentle detune shimmer."""
    tt = np.arange(int(SR * length)) / SR
    sig = np.zeros_like(tt)
    for f in freqs:
        for det in (-0.16, 0.16):      # slight chorus detune
            sig += np.sin(2 * np.pi * (f + det) * tt)
        sig += 0.18 * np.sin(2 * np.pi * f * 2 * tt)
    sig /= (len(freqs) * 2.18)
    # slow swell
    env = np.sin(np.pi * np.clip(tt / max(length, 1e-6), 0, 1)) ** 1.3
    return sig * env * amp


def bass(freq, length, amp=0.16):
    tt = np.arange(int(SR * length)) / SR
    sig = np.sin(2 * np.pi * freq * tt) + 0.22 * np.sin(2 * np.pi * freq * 2 * tt)
    env = adsr(len(tt), 0.03, 0.25, 0.55, 0.5)
    return sig * env * amp / 1.22


# note helpers
def nfreq(semitones_from_a4):
    return 440.0 * (2 ** (semitones_from_a4 / 12.0))


# C major pentatonic scale degrees (semitones from A4)
PENTA = [3, 5, 7, 10, 12, 15, 17, 19, 22, 24]   # C4 D4 E4 G4 A4 C5 D5 E5 G5 A5
CHORD_ROOTS = {  # C / Am / F / G  (I vi IV V) - warm, safe, resolved
    "C":  [-9, -2, 3, 7],     # C3 G3 C4 E4
    "Am": [-7, 0, 3, 8],      # A3 C4 E4 G4
    "F":  [-10, -1, 5, 8],    # F3 A3 C4 E4
    "G":  [-8, -3, 2, 7],     # G3 B3 D4 G4
}
BASS_ROOT = {"C": -21, "Am": -19, "F": -22, "G": -20}   # low octave

music = np.zeros(n, dtype=np.float64)

# ---- chord / bass bed: 2 chords per 8 beats, slow progression ----
chord_len = BEAT * 8
progression = ["C", "Am", "F", "G"]
chord_idx = 0
pos = 0.0
while pos < DUR:
    name = progression[chord_idx % len(progression)]
    length = min(chord_len, DUR - pos)
    if length <= 0.05:
        break
    place_at(music, pad_chord([nfreq(s) for s in CHORD_ROOTS[name]], length,
                              amp=0.085), pos)
    place_at(music, bass(nfreq(BASS_ROOT[name]), length * 0.92, amp=0.13), pos)
    pos += chord_len
    chord_idx += 1

# ---- sparse pentatonic bell melody ----
# gentle, unhurried phrases with plenty of space (so it never masks the voice)
phrase_a = [0, 2, 4, 3, 2, 0, 1, 0]
phrase_b = [3, 4, 6, 5, 4, 2, 3, 2]
phrases = [phrase_a, phrase_b]

step = BEAT / 2          # eighth notes
pos = BEAT * 2           # let the pad breathe first
pi = 0
m = 0
while pos < DUR - 0.3:
    ph = phrases[pi % len(phrases)]
    deg = ph[m % len(ph)]
    octave = 0
    while deg >= len(PENTA):
        deg -= len(PENTA)
        octave += 12
    semi = PENTA[deg] + octave
    length = step * 1.9
    sig = bell(nfreq(semi), min(length, DUR - pos),
               amp=0.20 if m % 2 == 0 else 0.15, bright=0.55)
    place(music, sig, pos, gain=1.0)
    pos += step
    m += 1
    if m % len(ph) == 0:
        pos += step * 2      # breathe between phrases
        pi += 1

# ---- master fades ----
music *= 0.92
fi = int(SR * 2.2)
fo = int(SR * 3.0)
music[:fi] *= np.linspace(0, 1, fi)
music[-fo:] *= np.linspace(1, 0, fo)

# ---- gentle stereo width ----
left = music + 0.16 * np.roll(music, int(SR * 0.012))
right = music + 0.16 * np.roll(music, -int(SR * 0.009))
stereo = np.stack([left, right], axis=1)

# soft clip + normalize to a comfortable -20 dBFS RMS bed
stereo = np.tanh(stereo * 1.25) / 1.25
peak = np.max(np.abs(stereo))
stereo = stereo / peak * 0.72
rms = np.sqrt(np.mean(stereo ** 2))
# Bed level: ~-25 dBFS RMS. The narration is loudnorm'd to about -16 LUFS, so
# this leaves a wide, safe gap before sidechain ducking is applied.
stereo = stereo / rms * 0.056

assert len(stereo) == n, (len(stereo), n)
pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())

print("bgm ->", OUT)
print("duration %.2fs  frames %d/%d  peak %.3f  rms %.4f (%.1f dBFS)"
      % (len(pcm) / 2 / SR, len(pcm), n, np.max(np.abs(stereo)), rms,
         20 * np.log10(rms)))

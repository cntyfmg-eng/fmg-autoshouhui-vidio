"""Rebuild a story video's audio: louder narration + ducked background music.

Chain:
  narration -> highpass -> loudnorm (-16 LUFS)  = clear, present voice
  bgm       -> (already quiet)                  = bed
  bgm ducked by narration via sidechaincompress = music dips under each line
  mix voice + ducked music, loudnorm -14 LUFS   = streaming-safe master

The video stream is copied, so this never re-encodes the picture.
"""
import os
import subprocess

from config import (FFMPEG, FFPROBE, WORK, ensure_dirs,
                    final_video_path)
ensure_dirs()

CURRENT = str(final_video_path())
BGM = os.path.join(str(WORK), "bgm.wav")
VOICE = os.path.join(str(WORK), "voice_boost.wav")
OUT = os.path.join(str(WORK), "audio_final.m4a")


def dur(path):
    o = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True)
    return float(o.stdout.strip())


def video_dur(path):
    """Authoritative duration = the VIDEO stream, so repeated runs cannot
    let the audio drift longer each pass."""
    o = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True)
    return float(o.stdout.strip())


target = video_dur(CURRENT)
print("target (video stream) duration: %.3fs" % target)

# ---------- 1. boost + normalize the narration ----------
# NOTE: rebuild the voice from the *unboosted* narration mix so repeated runs
# never compound the gain. tts_meta carries the original per-scene audio.
NARRATION_SRC = os.path.join(WORK, "narration_plain.m4a")
if not os.path.exists(NARRATION_SRC):
    raise SystemExit(
        "Missing clean narration source: %s\n"
        "Re-run assemble.py (it writes this) before mix_audio.py." % NARRATION_SRC
    )

run = subprocess.run([
    FFMPEG, "-y", "-i", NARRATION_SRC,
    "-vn",
    "-af", "atrim=0:%.3f,asetpts=N/SR/TB,highpass=f=90,lowpass=f=12000,"
          "loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.95" % target,
    "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", "-f", "wav",
    VOICE,
], capture_output=True, text=True)
if run.returncode != 0:
    raise SystemExit("voice boost failed:\n" + run.stderr[-3000:])
print("voice normalized -> %.2fs" % dur(VOICE))

# ---------- 2. mix voice (front) + ducked music (back) ----------
# sidechaincompress: bgm is "main", voice is the sidechain key -> when voice
# plays, bgm gain is reduced. Threshold is high (0.35) so the dip is gentle
# and only the loudest part of speech triggers it; ratio 3 keeps the music
# present. Base music sits ~ -22 dBFS, safely under the normalized voice.
filt = (
    # music: trim to length
    "[1:a]atrim=0:%.3f,asetpts=N/SR/TB[music];" % target +
    # voice: pad/trim to exact length (also the sidechain key)
    "[0:a]apad,atrim=0:%.3f,asetpts=N/SR/TB[voice];" % target +
    # gentle duck: high threshold, low ratio
    "[music][voice]sidechaincompress="
    "threshold=0.35:ratio=3:attack=30:release=600:makeup=1[ducked];" +
    # set the ducked bed to a fixed comfortable level under the voice
    "[ducked]volume=1.9[bed];" +
    # sum, then tame the peak for streaming (~ -14 LUFS, TP -1.5 dBTP)
    "[voice][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
    "loudnorm=I=-14:TP=-1.5:LRA=11[mix]"
)

run = subprocess.run([
    FFMPEG, "-y",
    "-i", VOICE, "-i", BGM,
    "-filter_complex", filt,
    "-map", "[mix]",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
    "-t", "%.3f" % target,          # hard-trim to the video length
    OUT,
], capture_output=True, text=True)
if run.returncode != 0:
    raise SystemExit("mix failed:\n" + run.stderr[-4000:])
print("mixed audio -> %.2fs" % dur(OUT))

# ---------- 3. replace the audio track in the video (copy video stream) ----------
FINAL = str(final_video_path())
TMP = os.path.join(WORK, "remux.mp4")
run = subprocess.run([
    FFMPEG, "-y", "-i", CURRENT, "-i", OUT,
    "-map", "0:v", "-map", "1:a",
    "-c:v", "copy", "-c:a", "copy",
    TMP,
], capture_output=True, text=True)
if run.returncode != 0:
    raise SystemExit("remux failed:\n" + run.stderr[-3000:])

os.replace(TMP, FINAL)
print("FINAL updated ->", FINAL)
print("duration: %.2fs" % dur(FINAL))

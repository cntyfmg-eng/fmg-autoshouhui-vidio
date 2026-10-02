"""Shared path configuration for the fmg-autoshouhui-vidio pipeline scripts.

All scripts read their paths from here so nothing is hardcoded to one machine.
Resolution order (first hit wins):

1. explicit CLI args (where the script accepts them)
2. environment variables
3. sensible defaults derived from the current working directory

Environment variables
---------------------
WORK            work dir for intermediates (tts/, covers, wavs, srt)
                  default: <cwd>/_work_shouhui
OUTDIR          final output directory                default: <cwd>
TITLE           story title used for the cover and file naming
STORY_VIDEO_PROJECT   renderer project root
                  default: %STORY_VIDEO_PROJECT% or ~/story-to-handdrawn-video
"""

from __future__ import annotations

import os
from pathlib import Path

TITLE = os.environ.get("TITLE", "手绘故事")
WORK = Path(os.environ.get("WORK", Path.cwd() / "_work_shouhui"))
TTS_DIR = WORK / "tts"
OUTDIR = Path(os.environ.get("OUTDIR", Path.cwd()))
PROJECT = Path(os.environ.get(
    "STORY_VIDEO_PROJECT", Path.home() / "story-to-handdrawn-video"))
FFMPEG = PROJECT / "ffmpeg-bin" / "ffmpeg.exe"
FFPROBE = PROJECT / "ffmpeg-bin" / "ffprobe.exe"
AUTOJY_SKILL = Path.home() / ".workbuddy" / "skills"

# TTS voice settings
VOICE = os.environ.get("TTS_VOICE", "zh-CN-XiaoxiaoNeural")
RATE = os.environ.get("TTS_RATE", "-8%")
PITCH = os.environ.get("TTS_PITCH", "+2Hz")

# per-scene timing padding (seconds)
LEAD = 0.55
TAIL = 1.15
COVER_PAD = 1.6

# 16:9 output
WIDTH, HEIGHT, FPS = 1920, 1080, 30

# Cover artwork: the ImageGen output you pass to make_cover.py.
# Set ART to the generated cover illustration (PNG/JPG); no text in it.
ART = os.environ.get("ART", str(WORK / "cover_art.png"))


def ensure_dirs() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    TTS_DIR.mkdir(parents=True, exist_ok=True)


def final_video_path() -> Path:
    return OUTDIR / f"{TITLE}.mp4"


def check_tools() -> None:
    """Fail fast with a clear message if the renderer's ffmpeg is missing."""
    for p in (FFMPEG, FFPROBE):
        if not p.exists():
            raise SystemExit(
                f"缺少 {p.name}。请先运行 scripts/check_env.py 并按指引部署：\n"
                f"  需要把完整 ffmpeg.exe / ffprobe.exe 及全部 ffmpeg 系列 DLL "
                f"放入 {FFMPEG.parent}\n"
                f"  详见 references/deployment.md")

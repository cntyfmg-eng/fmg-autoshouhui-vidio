#!/usr/bin/env python3
"""环境自检：逐项检查本技能所需依赖，缺失项给出修复指引。

纯标准库实现，可用系统 python 直接运行：
    python scripts/check_env.py
退出码 0 = 全部必须项就绪；1 = 有必须项缺失。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---- 探测位置（允许用环境变量覆盖） ----
PROJECT = Path(os.environ.get("STORY_VIDEO_PROJECT",
                              Path.home() / "story-to-handdrawn-video"))
FFMPEG_BIN = PROJECT / "ffmpeg-bin"
SKILL_DIR = Path(__file__).resolve().parent.parent
AUTOJY = Path.home() / ".workbuddy" / "skills"

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

# WorkBuddy 托管 venv 优先，其次系统 python
VENV_PY = Path(os.environ.get(
    "WORKBUDDY_VENV_PY",
    Path.home() / ".workbuddy" / "binaries" / "python" / "envs" / "default"
    / "Scripts" / "python.exe"))

PY_PKGS = ["edge_tts", "numpy", "PIL"]


def ok(msg):    print(f"  [OK]      {msg}")
def miss(msg):  print(f"  [MISSING] {msg}")
def opt(msg):   print(f"  [OPTIONAL] {msg}")


def section(title):
    print(f"\n=== {title} ===")


def check_python_interpreter():
    section("Python 解释器")
    if VENV_PY.exists():
        ok(f"托管 venv: {VENV_PY}")
        return VENV_PY
    miss(f"未找到托管 venv: {VENV_PY}")
    print("       修复: 在 WorkBuddy 中执行一次任意 Python 任务以创建 venv，"
          "或手动创建后 pip 安装 " + " ".join(PY_PKGS))
    return None


def check_py_packages(py):
    section("Python 依赖包")
    if not py:
        miss("无可用解释器，跳过")
        return
    try:
        code = ("import json\n"
                "out={}\n"
                "for m in %r:\n"
                "    try:\n"
                "        mod=__import__(m)\n"
                "        out[m]=getattr(mod,'__version__','ok')\n"
                "    except Exception:\n"
                "        out[m]=None\n"
                "print(json.dumps(out))\n" % (PY_PKGS,))
        r = subprocess.run([str(py), "-c", code], capture_output=True,
                           text=True, timeout=90)
        res = json.loads(r.stdout.strip() or "{}")
    except Exception as e:                                    # noqa: BLE001
        miss(f"探测失败: {e}")
        return
    missing = []
    for m in PY_PKGS:
        if res.get(m):
            ok(f"{m} {res[m]}")
        else:
            miss(f"python 包 {m}")
            missing.append(m)
    if missing:
        print(f"       修复: \"{py}\" -m pip install " + " ".join(missing))


def check_node():
    section("Node.js / npm")
    node = shutil.which("node")
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if node:
        v = subprocess.run([node, "--version"], capture_output=True,
                           text=True).stdout.strip()
        ok(f"node {v}")
    else:
        miss("node 未找到")
        print("       修复: 安装 Node.js 18+ (https://nodejs.org) 后重开终端")
    if npm:
        ok("npm 已找到")
    else:
        miss("npm 未找到")
    return node is not None and npm is not None


def check_project():
    section("渲染器项目 (story-to-handdrawn-video)")
    need = ["package.json", "scripts/story-to-video.mjs",
            "scripts/run_story_video.py"]
    if not PROJECT.exists():
        miss(f"项目目录不存在: {PROJECT}")
        print("       修复: git clone https://github.com/gnipbao/story-to-handdrawn-video "
              f'"{PROJECT}"')
        print("       克隆后按 references/deployment.md 打 EBUSY 补丁")
        return False
    absent = [n for n in need if not (PROJECT / n).exists()]
    if absent:
        miss("项目不完整，缺少: " + ", ".join(absent))
        return False
    ok(f"项目完整: {PROJECT}")
    if (PROJECT / "node_modules").exists():
        ok("node_modules 已安装")
    else:
        miss("node_modules 未安装")
        print(f'       修复: cd "{PROJECT}" && npm ci --ignore-scripts')
    return True


def check_ffmpeg():
    section("ffmpeg / ffprobe")
    local_ff = FFMPEG_BIN / "ffmpeg.exe"
    local_fp = FFMPEG_BIN / "ffprobe.exe"
    for label, p in (("ffmpeg.exe", local_ff), ("ffprobe.exe", local_fp)):
        if p.exists():
            ok(f"{label} (self-contained: {p})")
        else:
            miss(f"{label} 缺失于 {FFMPEG_BIN}")
    if not local_fp.exists():
        print("       修复: 把完整 ffprobe.exe + 全部 ffmpeg 系列 DLL 放入 "
              f"{FFMPEG_BIN}")
        print("       或设置环境变量后重跑；详见 references/deployment.md")
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        opt("系统 PATH 中也有 ffmpeg/ffprobe（自带版本优先）")


def check_browser():
    section("渲染浏览器 (Chromium 内核)")
    for b in BROWSERS:
        if Path(b).exists():
            ok(f"找到浏览器: {b}")
            print(f"       渲染时设置 REMOTION_CHROME_EXECUTABLE={b}")
            return
    if os.environ.get("REMOTION_CHROME_EXECUTABLE"):
        ok("已设置 REMOTION_CHROME_EXECUTABLE")
        return
    miss("未找到 Edge/Chrome")
    print("       修复: 安装 Microsoft Edge 或 Chrome；"
          "或设置 REMOTION_CHROME_EXECUTABLE 指向可执行文件")


def check_companion_skills():
    section("配套技能")
    if any(AUTOJY.glob("fmg-autojy-video*")):
        ok("fmg-autojy-video 已安装（配音/字幕/草稿由它负责）")
    else:
        miss("fmg-autojy-video 未安装")
        print("       本技能用它完成配音+字幕+草稿；缺失时只能出静音片，"
              "或改为手工配音")
    if any(AUTOJY.glob("story-to-handdrawn-video*")):
        ok("story-to-handdrawn-video 技能已安装")
    else:
        opt("story-to-handdrawn-video 技能未安装（渲染器项目仍可直接用 CLI）")


def check_style_gallery():
    section("离线风格图库 (可选)")
    g = PROJECT / "references" / "style-examples"
    if g.exists():
        n = sum(1 for _ in g.rglob("*.png")) + sum(1 for _ in g.rglob("*.jpg"))
        if n:
            ok(f"预览图 {n} 张")
            return
    opt("离线预览图库缺失/不完整 —— 仅影响风格浏览，不影响分镜/生图/渲染")


def main():
    print("fmg-autoshouhui-vidio 环境自检")
    print("=" * 46)
    py = check_python_interpreter()
    check_py_packages(py)
    node_ok = check_node()
    proj_ok = check_project()
    check_ffmpeg()
    check_browser()
    check_companion_skills()
    check_style_gallery()

    must = [node_ok, proj_ok]
    print("\n" + "=" * 46)
    if all(must):
        print("必须项全部就绪，可以开始生成流程。")
        return 0
    print("存在必须项缺失：请先按上面 [MISSING] 下的指引完成部署。")
    print("（未部署完成前只能交付分镜与提示词，不得声称已生成成片。）")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# 部署指南（本机一次性准备）

本技能依赖 Node、ffmpeg/ffprobe、一个 Chromium 内核浏览器、Python venv，以及
story-to-handdrawn-video 渲染器项目。**首次使用请先跑 `scripts/check_env.py`**，
它会逐项打印 `[OK] / [MISSING]` 并给出对应修复命令。

```bash
python scripts/check_env.py     # 纯标准库，系统 python 即可
# 有环境变量覆盖时：
STORY_VIDEO_PROJECT=/path/to/project python scripts/check_env.py
```

---

## 1. Node.js 18+ 与 npm

渲染器是一个 Remotion 项目，需要 node 与 npm。

- 检查：`node --version` / `npm --version`
- 缺失时：安装 Node.js LTS（https://nodejs.org）后**重开终端**

## 2. 渲染器项目 story-to-handdrawn-video

```bash
git clone https://github.com/gnipbao/story-to-handdrawn-video \
           "$HOME/story-to-handdrawn-video"
cd "$HOME/story-to-handdrawn-video"
npm ci --ignore-scripts
```

- 用 `--ignore-scripts` 是因为 esbuild 的 postinstall 在校验时会触发
  Windows `EBUSY` 文件锁报错；跳过即可，esbuild 仍可用。
- 关键文件应存在：`package.json`、`scripts/story-to-video.mjs`、
  `scripts/run_story_video.py`

> **网络提示**：某些网络下 `raw.githubusercontent` 批量下载不稳定，
> `references/style-examples/` 离线预览图库（约 663MB / 348 张）可能下不完整。
> 这**不影响**分镜 / 生图 / 渲染，只是风格浏览受限。稳定网络下重跑下载脚本，
> 或 `git clone` 完整仓库覆盖该目录即可。

## 3. 自包含 ffmpeg / ffprobe（关键）

渲染器要调 `ffprobe` 量图片尺寸、调 `ffmpeg` 做图层处理与编码。
**只放一个 `ffmpeg.exe` 不够**——`ffprobe.exe` 及其依赖的 ffmpeg 系列 DLL 必须齐全。

做法（任选其一）：

1. **从 Remotion 的 Windows 预编译包里取出**（本项目验证过的做法）：
   `@remotion/compositor-win32-x64-msvc` 里带真实 `ffprobe.exe`（约 169KB，动态链接），
   连同其全部 DLL（`avcodec-60/61`、`avformat-60/61`、`avutil-58/59`、
   `swscale-7/8`、`swresample-4/5`、`avfilter-9/10`、`avdevice-60/61`、
   `libgcc`/`libstdc++`/`zlib` 等）放进 `<项目>/ffmpeg-bin/`。
2. 或者用 gyan.dev 的**完整静态 build**（`ffmpeg.exe` + `ffprobe.exe` 同目录）。

把整个 `ffmpeg-bin/` 放进渲染器项目根目录，即做到自包含。

`scripts/run_story_video.py` 的 `prepare_environment()` 会自动把
`<项目>/ffmpeg-bin` 前置到 PATH，通常无需手动设 `PATH`。

## 4. 渲染浏览器（Chromium 内核）

Remotion 默认尝试下载 Chromium；部分网络下 `storage.googleapis.com` 不可达。
**用系统已装的 Microsoft Edge 或 Google Chrome 代替**即可：

```
REMOTION_CHROME_EXECUTABLE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
```

`prepare_environment()` 会在该变量未设置时自动探测 Edge/Chrome 的常见路径。

## 5. Python venv 与依赖

本技能的混音/配音/封面脚本需要 `edge_tts`、`numpy`、`Pillow`。
优先用 WorkBuddy 托管 venv：

```
$HOME/.workbuddy/binaries/python/envs/default/Scripts/python.exe
```

安装缺失包：

```bash
PY="$HOME/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" -m pip install edge-tts numpy Pillow
```

也可用环境变量 `WORKBUDDY_VENV_PY` 指向自己的解释器。

## 6. EBUSY 补丁（Windows 沙箱必需）

某些受限沙箱**完全禁止 Node 同步创建进程**（`spawnSync`/`execFileSync` 对任意
exe 都返回 `EBUSY`，连 `cmd /c echo` 也失败），而异步 `spawn` 正常。
渲染器在 `page-assets.mjs` 等处用 `execFileSync` 调 ffmpeg/ffprobe，会直接失败。

修复：把 `execFileSync` 换成本技能附带的 shim。

1. 复制 `assets/_spawn_sync_shim.mjs` 到项目 `scripts/`
2. 在 `page-assets.mjs`、`story-to-video.mjs`、`import-codex-images.mjs`、
   `package-project.mjs` 里把
   `import {execFileSync} from 'node:child_process'` 改为
   `import {execFileSyncShim as execFileSync} from './_spawn_sync_shim.mjs'`

shim 原理：以 `cmd.exe /c <临时.cmd>` 异步拉起子进程，stdout/stderr 重定向到文件、
退出码写入哨兵文件，父线程用 `Atomics.wait` 阻塞等哨兵出现后读结果。
子进程是独立 OS 进程，不受父线程阻塞影响。

> Remotion 内部自己的同步调用（`probe-encoder.js` 的 `execFileSync -encoders`、
> `get-cpu-count.js` 的 `execSync nproc`）已被 try/catch 包裹，EBUSY 时会回退到
> 软件编码 / `os.cpus()`，不影响渲染。

## 7. 16:9 版式补丁（可选，用于横屏版式）

渲染器默认按 3:4 排版。为支持 16:9 绘本式左右分栏
（右侧插画 + 左侧竖排字幕），用本技能 `assets/` 里的版本覆盖：

- `assets/LayerWipe.tsx` → `<项目>/src/LayerWipe.tsx`
- `assets/TextWipe.tsx` → `<项目>/src/TextWipe.tsx`

它们读 `useVideoConfig().width`，宽度 ≥1600 自动切横版布局，
竖屏（1080×1440）行为与原版一致。

## 8. 配套技能

- **fmg-autojy-video**：负责 AI 配音、字幕、剪映草稿。本技能的视频合成阶段会用到。
  缺失时只能出静音片，或改为手工配音。
- **story-to-handdrawn-video**：可选的技能封装；即便未安装，渲染器项目仍可直接用 CLI。

---

## 部署完成的判定

`check_env.py` 退出码为 0（"必须项全部就绪"）即表示可以开始生成流程。
若用户明确表示暂不安装，则**只交付分镜与提示词**，不得声称已生成成片。

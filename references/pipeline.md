# 端到端流水线（命令序列）

前置：已按 `deployment.md` 部署完成，`python scripts/check_env.py` 退出码 0。
以下命令中 `$PY` = WorkBuddy 托管 venv 的 python，脚本路径以本技能 `scripts/` 为例。

```bash
SKILL=~/.workbuddy/skills/fmg-autoshouhui-vidio
PY="$HOME/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
PROJ="$HOME/story-to-handdrawn-video"
```

---

## Step 0 分镜预切（长段落必做）

渲染器字幕上限是 **3 行 × 13 字**，超了直接抛
`Caption needs N lines; story beat must be split before rendering`。

把长段落切成「一文件一短句、一个完整句子」，写成 `<原名>_分镜.txt`。
**不要改写原句意思**，只按叙事转折点断句，句内不要出现 `！？` 等终止标点。

## Step 1 生成插画清单

```bash
cd "$PROJ"
python scripts/run_story_video.py \
  --input "/path/故事_分镜.txt" \
  --title "我家的杏熟了" \
  --text-mode font \
  --mode generate
```

产物：
- `codex-image-jobs.json`（顶层 `jobs[]`，每项含 `id`/`output_master`/`prompt`）
- `prompts/generated/codex/<asset_set>/*.txt`（每个 job 的完整 prompt）
- `storyboard.generated.json`

### ⚠ 必做：asset 目录改 ASCII

`<asset_set>` 默认是**故事标题 + 哈希**（含中文）。渲染器走子进程，
参数经 Windows GBK 代码页，中文目录名会让 ffprobe 收到乱码路径并
报 `Invalid argument` 而中断。**在 import 之前**改名：

```bash
cd "$PROJ"
# 把 <asset_set> 目录改为纯 ASCII，并同步替换两个 json 里的旧名
python - <<'PY'
import os, json, shutil
OLD, NEW = '我家的杏熟了-xxxxxxxx', 'my-story-xxxxxxxx'   # 换成你的
base = 'public/assets/generated/codex'
if os.path.isdir(os.path.join(base, OLD)):
    shutil.move(os.path.join(base, OLD), os.path.join(base, NEW))
for fn in ['codex-image-jobs.json', 'storyboard.generated.json']:
    t = open(fn, encoding='utf-8').read()
    open(fn, 'w', encoding='utf-8').write(t.replace(OLD, NEW))
    print(fn, 'patched')
PY
```

### 生成插画（串行！）

对每个 `role != 'reference'` 的 job，读取 `prompts/.../<id>_master.txt` 调 ImageGen：

- **必须串行**：并行会因同秒时间戳互相覆盖（实测 5 张只活 3 张）
- 每张用**独立 `output_dir`**，生成完立即 `cp` 到该 job 的 `output_master`
- prompt 保持原样（其中已含"do not add any text"）
- 另有一张 `00_character_reference.png` 同样要生成

校验：所有 `output_master` 都存在（分镜数 + 1）。

## Step 2 导入 + 渲染 3:4 静音版

```bash
python scripts/run_story_video.py --mode import \
  --manifest codex-image-jobs.json --text-mode font
python scripts/run_story_video.py --mode render
```

产出 `out/picture_silent.mp4`（1080×1440 / H.264 / 静音）。
**这一步即可交付"可后期配音"的竖版片**；若只需 3:4，到此为止。

## Step 3 16:9 重制 + 配音 + 封面 + 音乐

### 3a 先做配音，量出每句真实时长

```bash
export TITLE="我家的杏熟了"
export WORK="/path/to/工作目录/_work_shouhui"
export OUTDIR="/path/to/输出目录"
"$PY" "$SKILL/scripts/make_tts.py"
```

产出 `tts/NN.mp3`（22 句 + `cover.mp3`）与 `tts_meta.json`（含每句真实时长）。

### 3b 按配音时长重算场景时长，生成 16:9 storyboard

```bash
"$PY" "$SKILL/scripts/make_storyboard_16x9.py"
```

写出 `storyboard.16x9.json`（1920×1080，每场景
`duration_sec = 语音 + 0.55 + 1.15`）。

### 3c 渲染 16:9 静音版

`src/storyboard.ts` 固定 import `storyboard.json`，故临时换入再还原：

```bash
cd "$PROJ"
cp storyboard.json storyboard.portrait.bak.json
cp storyboard.16x9.json storyboard.json
export PATH="$PWD/ffmpeg-bin:$PATH"
export REMOTION_CHROME_EXECUTABLE="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
npx remotion render src/index.ts PictureSilent out/story_16x9_silent.mp4 \
  --codec=h264 --crf=18 --pixel-format=yuv420p --muted --concurrency=1
cp storyboard.portrait.bak.json storyboard.json   # 还原竖版
```

> 横版版式需要先按 `deployment.md` §7 覆盖 `LayerWipe.tsx` / `TextWipe.tsx`。

### 3d 生成封面插画（不带文字）+ 合成封面

用 ImageGen 生成封面场景（prompt 里明确 "Absolutely NO text"），
把结果路径给 `ART` 环境变量：

```bash
ART="/path/to/cover_art.png" "$PY" "$SKILL/scripts/make_cover.py"
```

`make_cover.py` 用 PIL 把插画贴右侧、用 `msyhbd.ttc` 写标题，
并**自动缩放标题**防止压到插画区。

### 3e 拼封面 + 旁白，产出旁白与外挂 SRT

```bash
"$PY" "$SKILL/scripts/assemble.py"
```

产出 `stage.mp4`（封面+分镜，无音轨）、`narration.m4a`（干净旁白）、`subtitles.srt`。

> **不要**在此处烧录 SRT：Remotion 已把文案烧进左栏，
> 再叠底部字幕会重复且压住插画。SRT 仅作外挂。

### 3f 提音量 + 背景音乐闪避 + 标准化

```bash
"$PY" "$SKILL/scripts/make_bgm.py"          # 现场合成版权安全的音乐床
"$PY" "$SKILL/scripts/make_narration_plain.py"  # 重建干净旁白（增益前）
"$PY" "$SKILL/scripts/mix_audio.py"         # 混音并替换音轨
```

`mix_audio.py` **只 copy 视频流**，不重编码画面。

## Step 4 验收

```bash
FFPROBE="$PROJ/ffmpeg-bin/ffprobe.exe"
FFMPEG="$PROJ/ffmpeg-bin/ffmpeg.exe"
F="$OUTDIR/$TITLE.mp4"

# 流与时长
"$FFPROBE" -v error -select_streams v:0 -show_entries stream=duration,nb_frames -of csv=p=0 "$F"
"$FFPROBE" -v error -select_streams a:0 -show_entries stream=duration,codec_name,channels -of csv=p=0 "$F"
# 响度：应约 -14 LUFS，峰值 ≤ -1.0 dBFS
"$FFMPEG" -i "$F" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+I:|Peak:"
# 解码无错
"$FFMPEG" -v error -i "$F" -f null -
```

抽帧检查（注意：**场景前 18% 右侧空白是"逐笔绘制"入场动画，属正常**，
应取场景中后段抽帧）：

```bash
"$FFMPEG" -y -ss 22.5 -i "$F" -frames:v 1 qa.png
```

判定标准：
- 分辨率 1920×1080、编码 h264 + aac、音视频时长一致
- 整体约 -14 LUFS、峰值 ≤ -1.0 dBFS
- 句间空档实测 -11~-17 dB（证明背景音乐一直垫着且不盖人声）

## 与 fmg-autojy-video 的分工

| 环节 | 负责方 |
|---|---|
| 分镜插画生成、3:4/16:9 渲染 | 本技能（story-to-handdrawn-video 渲染器） |
| 封面页、背景音乐、闪避混音、响度标准化 | 本技能脚本 |
| AI 配音（edge-tts）、外挂字幕、剪映草稿 | **fmg-autojy-video** |

需要剪映可编辑草稿时，用 fmg-autojy-video 的 `jy_draft.export_draft()`；
只要能播放的 MP4 时用本技能链路即可（不依赖剪映）。

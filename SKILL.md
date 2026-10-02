---
slug: fmg-autoshouhui-vidio
name: fmg-autoshouhui-vidio
version: 1.0.0
displayName: 手绘漫画故事视频一键生成（含配音/封面/背景音乐/字幕）
description: 把一段中文故事文本或有序图片，自动做成手绘漫画风格的 16:9 视频成片：先用 story-to-handdrawn-video 生成彩铅日记风分镜插画并渲染，再调用 fmg-autojy-video 合成 AI 配音、封面页、背景音乐（自动闪避不压人声）与字幕。首次使用会先引导完成本机依赖下载与部署自检。
agent_created: true
---

# fmg-autoshouhui-vidio 手绘漫画故事视频一键生成

把「一段中文故事」变成「一条可直接发布的手绘漫画视频」，一条命令跑完：
**分镜 → 插画 → 渲染 → 配音 → 封面 → 背景音乐 → 字幕 → 成片**。

## 0. 首次使用：必须先完成部署（硬性前置）

本技能需要 Node、ffmpeg/ffprobe、一个 Chromium 内核浏览器、Python 虚拟环境，
以及 story-to-handdrawn-video 渲染器项目。**在用户首次触发本技能时，先执行部署自检**：

```bash
python scripts/check_env.py            # Windows 默认 python 即可，纯标准库
```

脚本会逐项打印 `[OK] / [MISSING]`，并给出该缺失项的修复指引。
**只要有 `[MISSING]`，就先引导用户完成对应安装，再继续生成流程。**

向用户汇报时要明确区分：
- **必须项**（缺了不能出片）：Node、ffmpeg-bin（ffmpeg+ffprobe+DLL）、浏览器、渲染器项目
- **可选项**（缺失只影响风格库浏览）：`references/style-examples/` 离线预览图库

若用户明确表示"暂不安装"，则只做**方案与分镜/提示词**层面的交付，**不得**声称已生成成片。

## 1. 铁律（每条都对应一个已踩过的坑）

1. **ImageGen 必须串行调用。** 并行会因同秒时间戳互相覆盖（5 张只活 3 张）。
   每张用独立 `output_dir`，生成完立刻拷到 `output_master`。
2. **asset 目录名必须纯 ASCII。** 渲染器走子进程，参数经 GBK 代码页，
   中文目录名会让 ffprobe 收到乱码路径并报 "Invalid argument"。生成前先改成 `wojiadexing-<hash>` 之类。
3. **字幕走 `--text-mode font`**，不要用 `image2`。`image2` 把中文画进图片里不可靠；
   `font` 由渲染器用系统中文字体叠加，每句清晰可读，便于后期配音对轴。
4. **长句先切分镜。** 字幕上限是 3 行 × 13 字，超了直接抛
   `Caption needs N lines`。一个 beat 放一个完整短句。
5. **插画里不要写字。** 标题/文字一律后期用真实字体（PIL + msyh.ttc）合成，避免 AI 出图乱码。
6. **配音时长驱动画面时长。** 先用 edge-tts 合成并量出每句真实时长，再设
   `duration_sec = 语音 + 0.55 + 1.15`，做到声画对齐。
7. **加封面后配音要补封面偏移。** 音频 `adelay` 记得加 `cover_dur`，
   并用 `apad,atrim` 对齐总长，否则音画错位、`-shortest` 会把片子截短。
8. **不要重复烧录 SRT。** 渲染器已把文案烧进画面左栏，再叠底部字幕会重复且压住插画。
9. **混音从干净旁白出发。** 不要从成片里再抽音轨做增益，会二次放大；
   每次都从 `make_narration_plain.py` 重建的 `narration_plain.m4a` 出发。
10. **`target` 取 video stream duration**（`-select_streams v:0`），不是 format duration，否则重跑会累积漂移。
11. **sidechaincompress 参数别手重。** 阈值太低会把音乐压没（-44dB 听不见），
    用本技能默认的 `threshold=0.35:ratio=3:attack=30:release=600`（音乐 ≈ -20dB，人声 ≈ -15dB）。
12. **Windows 沙箱禁止 Node 同步建进程**（EBUSY）。用 `scripts/_spawn_sync_shim.mjs` 兜底，
    详见 `references/deployment.md`。

## 2. 标准工作流

### Step 1 备料
- 读用户故事。若是长段落，先切分成一文件一短句的 `<原名>_分镜.txt`（**不得改写原句意思**）。
- 跑 `python scripts/check_env.py`；有缺失先部署。

### Step 2 生成插画（串行！）
在渲染器项目根目录执行 `--mode generate`，得到
`codex-image-jobs.json`（`jobs[]`，每项含 `id` / `output_master` / `prompt`）
与 `prompts/generated/codex/<asset_set>/*.txt`。

- `output_master` 落在**含中文的目录** → **先按铁律 2 改成 ASCII**，再让 import 通过。
- 逐个 job 取对应 prompt 调 ImageGen（铁律 1、5），拷到 `output_master`。
- 校验：`jobs` 全部 `output_master` 存在（应 = 分镜数 + 1 张角色参考）。

### Step 3 导入 + 渲染
```bash
python scripts/run_story_video.py --mode import --manifest codex-image-jobs.json --text-mode font
python scripts/run_story_video.py --mode render
```
产出 `out/picture_silent.mp4`（3:4 静音版，可直接交付给用户做纯配音版）。

### Step 4 16:9 重制（可选，但推荐）
本技能已把 `LayerWipe.tsx` / `TextWipe.tsx` 改成**自适应**（宽度 ≥1600 自动切横版：
右侧插画 + 左栏字幕），并提供 `scripts/make_storyboard_16x9.py`：
先按配音时长重算每场景 `duration_sec`，再把 `storyboard.16x9.json` 临时换入
`storyboard.json` 后渲染，渲完还原（脚本自带备份/还原）。

### Step 5 配音 + 封面 + 音乐（调用 fmg-autojy-video）
用**用户已安装的 `fmg-autojy-video` 技能**完成配音/字幕/草稿，用本技能脚本完成
背景音乐与闪避混音。顺序与命令见 `references/pipeline.md`。

### Step 6 验收
- ffprobe 核对：分辨率 / 编码 / 时长 / 音视频流齐全
- 抽帧：封面标题在左栏、插画在右、字幕可见
- `ebur128`：成片约 **-14 LUFS**、峰值 ≤ -1.0 dBFS
- 句间空档实测 -11~-17 dB → 证明背景音乐一直垫着

## 3. 脚本索引

| 脚本 | 作用 |
|---|---|
| `scripts/check_env.py` | 部署自检，缺什么给什么指引 |
| `scripts/make_storyboard_16x9.py` | 按配音时长重算时长并生成 16:9 storyboard |
| `scripts/make_tts.py` | edge-tts 逐句配音 + 量真实时长 |
| `scripts/make_narration_plain.py` | 由 tts_meta 重建**干净**旁白（增益前） |
| `scripts/make_cover.py` | PIL 合成封面（插画 + 中文标题，自动缩放防压图） |
| `scripts/make_bgm.py` | numpy **现场合成**版权安全的背景音乐 |
| `scripts/assemble.py` | 拼封面 + 分镜，生成旁白与外挂 SRT |
| `scripts/mix_audio.py` | 提音量 + 音乐闪避 + 标准化混音（视频流 copy 不重编码） |

## 4. 交付要求

- 主交付：`我家的杏熟了.mp4`（16:9 / H.264+AAC / 约 -14 LUFS）
- 附带：封面 PNG、**外挂** SRT（可选导入）
- 明确告知：分辨率、时长、是否静音、音量标准
- **未实际渲染出片时，不得声称"已生成视频"**；只能交付分镜、提示词与方案。

## 参考文档
- `references/deployment.md` — 依赖清单、EBUSY 补丁、离线图库说明
- `references/pipeline.md` — 端到端命令序列与逐参数取值理由
- `references/pitfalls.md` — 全部踩坑记录与症状→根因→修复

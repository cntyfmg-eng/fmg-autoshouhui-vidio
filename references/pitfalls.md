# 踩坑记录（症状 → 根因 → 修复）

全部来自一次真实完整的《我家的杏熟了》16:9 配音成片制作过程。

---

## 1. 字幕超长直接中断

**症状**
```
Error: Caption needs 4 lines; story beat must be split before rendering
```
**根因**：`formatCaption(text, maxCharsPerLine=13, maxLines=3)` 上限 3 行 × 13 字。
原文 11 个长段落里有含 `！？` 的引语，展开后超过 3 行。

**修复**：生成前把长段落预切成 22 个短 beat（一文件一完整短句，句内无终止标点），
写成 `<原名>_分镜.txt` 再喂给 `--input`。**不改写原句意思。**

---

## 2. ImageGen 并行调用互相覆盖

**症状**：5 张并行，返回的 `localPath` 全落在同一个目录，
结果只剩 3 个文件（另外 2 个被同秒时间戳覆盖）；第二次用不同 `output_dir`
仍然全部堆到 `s06`，只活 3 张。

**根因**：并行调用时输出文件用**秒级时间戳**命名，落在同一目录即互相覆盖；
且返回的 `localPath` 在并发下不可靠。

**修复**：**串行**逐张生成，每张独立 `output_dir`，生成完立即 `cp` 到
`output_master`。20 张一次全部到位。

---

## 3. 中文 asset 目录名让 ffprobe 报 "Invalid argument"（最隐蔽）

**症状**
```
Error: Command failed: ffprobe ... 01_master.png
.../鎴戝...鐔熶簡-1dd8b82d/01_master.png: Invalid argument
```
**根因**：`--mode import` 用 Node `execFileSync` 拉起 ffprobe，
Windows 下参数走 **GBK 代码页**，asset 目录名 `我家的杏熟了-xxx` 被转成乱码，
ffprobe 找不到文件。报错里 mojibake 路径就是证据。

**修复**：把 asset 目录改成**纯 ASCII**（`my-story-xxx`），
并同步替换 `codex-image-jobs.json` 与 `storyboard.generated.json`
里的所有旧名（前者 69 处、后者 44 处）。import 立刻通过。

**通用规则**：该渲染器全链路走子进程与文件路径，**asset_set 命名务必纯 ASCII**。

---

## 4. 中文字幕用 image2 模式不可靠

**症状**：`--text-mode image2` 把中文画进插画里，字形乱/缺笔画。

**修复**：改用 `--text-mode font`。此时 `usesImage2Text=false`，
master prompt 自动带 "do not add any text"，
由渲染器 `TextWipe.tsx` 用系统中文字体（PingFang / 微软雅黑）叠加 `scene.text`，
每句清晰可读，便于后期配音对轴。

> 附带好处：font 模式 + `--layout full` 会跳过字幕区检测，
> 直接由整幅插画派生彩铅/黑白图层。

---

## 5. 加封面后配音比画面早 + 成片被截短

**症状**：视频 124.8s、音频只有 120.2s，成片尾部被截；
音画整体错位约 3.6s（正好是封面时长）。

**根因**（两个叠加）：
1. 混旁白时 `adelay` 用的是**场景时间轴**，没加封面偏移；
2. `-shortest` 取两者较短，把视频截到音频长度。

**修复**：
- 音频每句 `adelay` 统一 `+ cover_dur`
- 汇总后 `apad,atrim=0:<video_dur>` 把音频补齐/截齐
- 再加 `-t <video_dur>` 硬截

---

## 6. 重跑导致增益累积 + 时长漂移

**症状**：每跑一次混音音量大一点、时长长 0.2s。

**根因**：
1. 从成片里再抽音轨做 `loudnorm` → 对已放大的音频二次放大；
2. `target` 取的是 `format duration`（容器总长，含被拉长的音频），
   于是每轮都把目标调大。

**修复**：
1. 每次都从 `make_narration_plain.py` 重建的**干净旁白**出发；
2. `target` 必须取 **video stream duration**：
   `ffprobe -select_streams v:0 -show_entries stream=duration`。

---

## 7. sidechaincompress 把音乐压没了

**症状**：音乐几乎听不见，音乐床实测 **-44 dB**。

**根因**：`threshold=0.02:ratio=8` 太敏感——旁白连续不断，
几乎全程都在触发压缩，音乐被持续压掉约 13 dB。

**修复**：改用柔和参数
```
threshold=0.35  ratio=3  attack=30  release=600
```
结果：音乐床 **-20 dB**、人声 **-15 dB**，约 5 dB 差值——
音乐可闻但 firmly 待在背景里。

---

## 8. 响度过热

**症状**：混完整体 -11.9 LUFS，峰值 -1.1 dBFS（接近削波）。

**修复**：汇总后再过一次 `loudnorm=I=-14:TP=-1.5:LRA=11`。
成片实测 **-14.0 LUFS / 峰值 -1.4 dBFS**，流媒体安全。

---

## 9. 底部字幕与左栏字幕重复且压住插画

**症状**：底部字幕带落在 x470-1408，正好压在右侧插画上；
内容与左栏烧录的文案完全重复。

**根因**：Remotion 的 font 模式**已经把文案烧进画面**了，再叠 SRT 属于重复。

**修复**：**不要烧录 SRT**。SRT 仅作为**外挂字幕**保留（可选导入）。
若确实需要烧字幕（如平台自动提取），应关掉渲染器内嵌文案或改用纯画面版式。

---

## 10. 封面标题压到插画

**症状**：标题宽 792px（132px 字号），而插画区从 x=798 开始 —— 重叠。

**修复**：`make_cover.py` 加 `fit_font()` 自动缩放，把标题限制在栏宽
（96..664 = 568px）内。实测收敛到 564px，零重叠。

> 通用经验：**AI 出图里不要写字**，文字一律后期用真实字体合成，
> 既保证字形正确，又能精确控制排版不压图。

---

## 11. Windows 沙箱禁止 Node 同步建进程（EBUSY）

**症状**：`errno:-4082 code:'EBUSY' syscall:'spawnSync'`，连 `cmd /c echo` 都失败。

**根因**：受限沙箱完全禁止 `spawnSync`/`execFileSync`（对任意 exe），
但**异步 `spawn` 正常**。

**修复**：用 `assets/_spawn_sync_shim.mjs` 把 `execFileSync` 换成
`cmd.exe /c <临时.cmd>` 异步拉起 + `Atomics.wait` 等哨兵文件。
详见 `deployment.md` §6。

---

## 12. 抽帧看到右侧空白——不是丢图

**症状**：抽帧落在场景前 18% 时，右侧插画区整片白。

**根因**：`Scene.tsx` 的"逐笔绘制"入场动画——bw 底片从 18% 才开始显现，
彩铅层从 52% 才开始。场景开头本来就是空白纸面。

**修复**：**取场景中后段抽帧**判断。
经验值：`t = 场景起点 + 0.7 × 场景时长`。

---

## 13. npm postinstall 触发 EBUSY

**症状**：`npm ci` 在校验时因 esbuild 的 postinstall 报文件锁错误。

**修复**：`npm ci --ignore-scripts`。esbuild 0.28+ 本身可用，跳过即可。

---

## 14. 混音时 MP4 容器装不下 PCM

**症状**：
```
Could not find tag for codec pcm_s16le ... codec not currently supported
```
**修复**：中间音频文件用 `.wav`（配 `-f wav`），只有最终音轨用 AAC。

---

## 15. 并行 ffmpeg 输入索引算错

**症状**：
```
Error binding filtergraph inputs/outputs: Invalid argument
Invalid file index 23 ...
```
**根因**：`adelay` 的输入序号用 `len(inputs)//2` 推导，
在"先 append 再算序号"时偏移 1。

**修复**：显式维护 `idx` 计数器——输入 0 是封面音，场景从 1 开始。

---

## 16. 打包/发布坑

- **不要把 `_icon.png` 放进发布文件**：SkillHub 会返回 400
  `不允许的文件类型: _icon.png`。图标改用 `payload.iconUrl` 传 URL。
- `_meta.json` / `_skillhub_meta.json` 同样排除，只传真正的技能内容。
- 发布域名是 **`api.skillhub.cn`**，不是 `skillhub.cn`
  （后者只托管 SPA，任何路径都返回 index.html，会造成"HTTP 200 但返回 HTML"的假象）。

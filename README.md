# 手绘漫画故事视频一键生成（含配音/封面/背景音乐/字幕）

把一段中文故事文本或有序图片，自动做成手绘漫画风格的 16:9 视频成片：先用 story-to-handdrawn-video 生成彩铅日记风分镜插画并渲染，再调用 fmg-autojy-video 合成 AI 配音、封面页、背景音乐（自动闪避不压人声）与字幕。首次使用会先引导完成本机依赖下载与部署自检。

一个 WorkBuddy Skill，把可复用的工作流固化下来，供随时调用。

## 文件结构

```
fmg-autoshouhui-vidio/
├── SKILL.md            # Skill 定义(入口, 含 front matter)
├── icon.png            # 图标
├── references/         # 参考模板 / 资料 / 数据
├── scripts/            # 自动化脚本(若有)
├── README.md
├── LICENSE
└── .gitignore
```

## 安装

将本仓库内容放入 WorkBuddy 的 skills 目录(`~/.workbuddy/skills/fmg-autoshouhui-vidio/`), 重启或刷新即可。

## License

MIT © cntyfmg-eng

# jike-to-obsidian-sync-skill

把自己的即刻内容持续同步到 Obsidian，按月份归档成 Markdown，并记住上次同步位置。

## 功能

- 使用即刻网页端登录态进行抓取
- 优先复用即刻网页自己的接口，获取稳定帖子 ID 和绝对时间
- 按 `YYYY-MM.md` 归档到 Obsidian
- 默认将图片和视频备份到本地 `assets/jike/` 目录
- Markdown 优先引用本地媒体文件，确保长期可回看
- 每条动态都会保留话题信息
- 时间标题直接链接到即刻原文
- 支持增量同步和历史回填
- 自动生成简体中文月度总结
- 自动生成 Obsidian 归档索引页

## 目录结构

```text
jike-to-obsidian-sync-skill/
├── SKILL.md
├── README.md
├── references/
└── scripts/
```

## 环境准备

本 Skill 使用自己的虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
./scripts/bootstrap.sh
```

## 快速开始

首次运行时，脚本会打开浏览器，你登录即刻后即可开始同步：

```bash
./scripts/sync-now.sh
```

也可以手动指定即刻个人页和 Obsidian 输出目录：

```bash
JKE_START_URL="https://web.okjike.com/u/your-profile" \
JKE_OUTPUT_ROOT="/path/to/your/Obsidian-vault" \
./scripts/sync-now.sh
```

## 产出文件

- `YYYY-MM.md`：每月归档文件
- `即刻归档索引.md`：Obsidian 索引页
- `assets/jike/YYYY-MM/`：本地媒体备份
- `.jike-sync/state.json`：同步状态
- `.jike-sync/items.jsonl`：规范化后的本地数据
- `.jike-sync/browser-profile/`：持久登录态

## 说明

更详细的工作流、命令和格式约定见 [SKILL.md](./SKILL.md)。

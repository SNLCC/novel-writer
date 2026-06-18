# Novel Writer — Codex Skill

> 长篇小说创作助手：故事圣经 + 多层大纲 + 人物档案 + 悬念追踪，四大系统强制联动，确保设定一致性。

## 解决的问题

用 AI 写长篇小说最大的痛点：**前章说东、后章说西**。人物性格漂移、伏笔忘了回收、世界观规则前后矛盾——写到 50 章就崩了。

Novel Writer 用一套「宪法-规划-执行」三层架构解决这个问题：

```
story-bible.md（宪法：不可随意改）
    ↓ 引用
outline/ + characters/（规划：调需确认）
    ↓ 实现
chapters/（执行：逐章迭代）
    ↓ 反向同步
suspense-tracking.md（追踪：每章更新）
```

## 快速开始

### 安装

```bash
# 方式 1：通过 Codex 安装
# 在 Codex 对话中输入：
/install-skill https://github.com/<你的用户名>/novel-writer

# 方式 2：手动安装
git clone https://github.com/<你的用户名>/novel-writer.git
cp -r novel-writer ~/.codex/skills/novel-writer
```

### 创建第一部小说

在 Codex 中说：

> 「帮我创建一个玄幻小说项目」

或者手动运行：

```bash
python scripts/new_novel.py 仙道长生 --path ./stories
```

### 写第一章

```bash
python scripts/init_chapter.py 1
# → 生成 PRE-FLIGHT 检查清单
# → 逐项确认后开始写正文
# → 写完后 python scripts/update_suspense.py --chapter 1
```

## 核心脚本

| 脚本 | 作用 |
|------|------|
| `guide.py` | 诊断当前状态，告诉下一步该做什么 |
| `new_novel.py` | 创建小说项目骨架 |
| `list_novels.py` | 列出/切换多部小说 |
| `init_chapter.py` | 生成章节 PRE-FLIGHT + 草稿 |
| `validate_preflight.py` | PRE-FLIGHT 强制校验（不通过不写） |
| `init_character.py` | 创建人物档案（Want/Need/弧线） |
| `new_arc.py` | 按需生成新卷大纲 |
| `check_consistency.py` | 5 项一致性检查（人物/悬念/计数/大纲/弧线） |
| `update_suspense.py` | 交互式悬念回收/新埋 |

## 项目结构

每个小说项目包含：

```
stories/我的小说/
├── story-bible.md              # 🌍 世界观宪法（唯一权威）
├── outline/
│   ├── master.md               # 全书大纲 + 人物弧线终点
│   └── arc-01.md ~ arc-NN.md   # 各卷大纲（钩子标注）
├── characters/
│   └── <人物名>.md             # 独立人物档案
├── chapters/
│   └── ch-01.md ~ ch-NN.md     # 章节正文 + PRE-FLIGHT
├── notes/
│   └── suspense-tracking.md    # 悬念追踪表
├── research/
│   └── competitor-sampling.md  # 竞品采样
├── meta.md                     # 元信息
└── timeline.md                 # 故事时间线
```

## 工作流

```
设定阶段（一次性）
  竞品采样 → 故事圣经 → 全书大纲 → 人物档案 → 分卷大纲

写作循环（每章）
  init_chapter → validate_preflight → 读4文件 → 写正文
  → update_suspense → 同步圣经/人物 → 标记完成

检查循环（每卷/每10章）
  check_consistency → 修问题 → 继续写
```

## 适用平台

支持番茄小说、起点、晋江等主流网文平台。Skill 内置了各平台的节奏策略和读者留存技巧。

## 许可证

MIT

# Novel Writer — Codex Skill `v1.0.0`

> 🧬 自进化长篇小说创作助手：故事圣经 + 多层大纲 + 人物档案 + 悬念追踪 + 场景档案 + 线索管理 + 共享知识库，七大系统强制联动。写的小说越多，Skill 自身越强。

## 解决的问题

用 AI 写长篇小说最大的痛点：**前章说东、后章说西**。人物性格漂移、伏笔忘了回收、世界观规则前后矛盾——写到 50 章就崩了。

Novel Writer 用一套「宪法-规划-执行」三层架构解决这个问题：

```
story-bible.md（宪法：不可随意改）
    ↓ 引用
outline/ + characters/ + scenes/（规划：调需确认）
    ↓ 实现
chapters/（执行：逐章迭代）
    ↓ 反向同步
suspense-tracking.md + clue-tracking（追踪：每章更新）
```

## 快速开始

### 安装

```bash
# 方式 1：通过 Codex 安装
# 在 Codex 对话中输入：
/install-skill https://github.com/SNLCC/novel-writer

# 方式 2：手动安装
git clone https://github.com/SNLCC/novel-writer.git
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
| `list_novels.py` | 列出/切换多部小说（同步 master-index.md） |
| `init_chapter.py` | 生成章节 PRE-FLIGHT + 草稿 |
| `validate_preflight.py` | PRE-FLIGHT 强制校验（不通过不写） |
| `init_character.py` | 创建人物档案（Want/Need/弧线） |
| `init_scene.py` | 🆕 创建场景档案（描写锚点/规则） |
| `new_arc.py` | 按需生成新卷大纲 |
| `append_bible.py` | 🆕 追加设定到故事圣经（自动去重） |
| `retention_check.py` | 🆕 章节留存质量自检（冲突/情绪/行动比/钩子/好奇心/信息密度/事件） |
| `check_consistency.py` | 7 项一致性检查（人物/悬念/场景/线索/计数/大纲/弧线） |
| `check_scenes.py` | 🆕 场景漂移检测 |
| `review.py` | 🆕 结构化复盘（卷/全书/章节批） |
| `evolve.py` | 🧬 Skill 自我进化引擎（随着小说积累自动变强） |
| `sync_library.py` | 🆕 跨项目模式提取到共享库 |
| `update_meta.py` | 🆕 自动更新 meta.md + timeline.md |
| `track_clue.py` | 🆕 悬念/线索/伏笔统一管理 |
| `update_suspense.py` | 交互式悬念回收/新埋（支持类型标注） |

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
├── scenes/
│   └── <场景名>.md              # 🆕 场景档案（描写锚点/规则/出场记录）
├── notes/
│   └── suspense-tracking.md    # 悬念/线索/伏笔追踪表（含类型标注）
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
  init_chapter → validate_preflight → 读5文件 → 写正文
  → update_suspense → retention_check（留存自检）
  → 同步圣经(append_bible)/人物/场景 → update_meta → 标记完成

检查循环（每卷/每10章）
  check_consistency → 修问题 → 继续写
```

## 许可证

MIT

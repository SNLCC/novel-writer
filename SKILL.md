---
name: novel-writer
description: 长篇小说创作助手，通过故事圣经、多层大纲、人物档案、悬念追踪四大系统的强制联动确保设定一致性。支持多部小说管理。当用户需要：（1）创建新小说项目并搭建世界观/大纲/人物体系，（2）逐章写作并保持情节连贯，（3）检查角色/剧情/伏笔一致性，（4）为网文平台优化节奏和钩子设计时使用。
---

# Novel Writer

## 用户引导（首次触发必读）

**每次被触发时，必须先运行 `python scripts/guide.py` 诊断当前状态**，根据输出引导用户走下一步。

### 引导决策树

```
guide.py 输出什么？
│
├─ "还没有任何小说项目"
│   → 询问：目标平台？类型？有无对标作品？
│   → 立即加载 references/platform-research.md，帮用户做竞品采样
│   → 然后运行 new_novel.py 创建项目
│
├─ "故事圣经: empty / missing"
│   → 引导用户逐一填写 story-bible.md 各板块
│   → 一次只引导一个板块，不要全抛
│
├─ "全书大纲: empty"
│   → 讨论：故事梗概 → 4卷结构 → 5个核心事件 → 人物弧线终点
│   → 核心事件和终点必须用户明确确认
│
├─ "人物档案: 0"
│   → 从大纲提取人物，逐一运行 init_character.py
│   → 每个人物的 Want / Need / 致命缺陷 必须和用户讨论后确定
│
├─ "第一卷大纲: empty"
│   → 逐章讨论 arc-01.md 的钩子类型和核心冲突
│   → 此时加载 references/reader-retention.md，确保钩子设计符合平台规律
│
├─ [设定完成，章节数 = N]
│   → 运行 init_chapter.py N+1
│   → 然后严格走 7 步循环（见下方）
│
└─ "发现 X 个问题"
    → 运行 check_consistency.py 展示具体问题，按优先级逐个处理
```

### 关键交互原则

- **一次只做一件事**。不要列出所有待办，引导用户一步一步来。
- **讨论重于填写**。圣经、大纲、人物设定要先讨论再落笔。
- **关键决策需用户确认**。核心事件、弧线终点、悬念计划回收章——必须用户点头。
- **PRE-FLIGHT 不可跳过**。写任何章节正文前，必须通过 validate_preflight.py。

---

## 何时加载参考文档

以下触发条件是**强制性的**——只要条件满足，立即加载对应参考文档：

### `references/platform-research.md`
**触发条件**（满足任一即加载）：
- 用户说要创建新小说、且尚未确定平台/类型
- 用户提到「番茄」「起点」「晋江」等平台名
- guide.py 显示「还没有任何小说项目」
- 用户在设定阶段、尚未完成竞品采样

### `references/reader-retention.md`
**触发条件**（满足任一即加载）：
- 用户开始填写 arc-01.md 的章节钩子类型
- 用户说「节奏」「爽点」「钩子」「留人」「读者流失」
- 写章节时、PRE-FLIGHT 中钩子类型为「待定」
- 章节写完后用户反馈「太平淡」「不够吸引人」
- 每 10 章做一次节奏检查时

---

## 核心架构：3 层信息流

```
第 1 层 · 源头（不可随意改）
  story-bible.md          ← 世界观宪法、核心规则
  ─────────────────────
第 2 层 · 规划（调需确认）
  outline/master.md       ← 全书大纲 + 5个核心事件
  outline/arc-0X.md       ← 每卷大纲（钩子类型标注）
  characters/<名字>.md    ← 人物档案 + 弧线追踪
  ─────────────────────
第 3 层 · 执行（逐章迭代）
  chapters/ch-XX.md       ← 章节正文 + 钩子实现
  ─────────────────────
旁路 · 追踪（每章更新）
  notes/suspense-tracking.md  ← 悬念回收 + 新埋
```

**数据流规则**：
- 任何新设定 → 先写 story-bible.md，再写章节
- 任何人物变化 → 同步更新 characters/<名字>.md 的出场记录表
- 任何悬念 → 必须登记到 suspense-tracking.md，必须有回收计划
- 禁止孤儿悬念（超过计划回收章 10 章仍未回收）

---

## 快速开始

```bash
python scripts/new_novel.py <小说名> --path ./stories   # 创建 + 自动设为当前
python scripts/list_novels.py --path ./stories           # 查看所有
python scripts/list_novels.py --path ./stories --set <名> # 切换当前
python scripts/guide.py                                  # 诊断状态
```

---

## 完整工作流

### 阶段一：设定

1. 竞品采样（加载 references/platform-research.md）
2. 故事圣经 → story-bible.md
3. 全书大纲 → outline/master.md
4. 人物档案 → init_character.py 逐一创建
5. 第一卷大纲 → arc-01.md（加载 references/reader-retention.md）
6. 后续卷 → new_arc.py 按需生成

### 阶段二：逐章写作（7 步循环）

```
① python scripts/init_chapter.py <N>     ← 生成 PRE-FLIGHT + 草稿
② python scripts/validate_preflight.py <N>  ← ⚠️ 强制检查！不通过不写
③ 实际阅读 4 份文件（story-bible / outline arc / suspense / characters）
④ 在章节文件中勾选 PRE-FLIGHT 清单，写正文
⑤ python scripts/update_suspense.py --chapter <N>  ← 悬念回收 + 新埋
⑥ 同步：圣经/人物档案/元信息如有变化立即更新
⑦ 标记章节为「已完成」
```

> ⚠️ **PRE-FLIGHT 是硬约束**：步骤② `validate_preflight.py` 返回非 0 则**不得开始写正文**。必须先确认钩子类型、前300字冲突、4 份文件、悬念回收都已完成。

### 阶段三：一致性检查

```bash
python scripts/check_consistency.py
```

5 项检查：人物档案完整性 / 悬念追踪 / 章节计数 / 大纲匹配 / **人物弧线更新**。

---

## 修订流程

当小说进入「修订中」状态（修改已完成初稿的章节）：

1. 将 meta.md 状态改为「🔵 修订中」
2. 确定修订范围（单章 / 整卷 / 全书）
3. **修订前先跑 check_consistency.py**，记住当前问题列表
4. 修改章节正文，在「写后归档」区域加 `[修订]` 标签
5. **每改完一章立即：**
   - 检查是否影响 story-bible（新设定 / 规则变化）→ 同步
   - 检查是否影响人物弧线 → 更新 characters/
   - 检查是否影响悬念 → 更新 suspense-tracking.md
6. 修订完成后跑 check_consistency.py，确保没有引入新问题
7. 状态改回「🟢 连载中」或「⚪ 已完结」

> 修订期间写新章同理——PRE-FLIGHT 不可跳过。

---

## 脚本索引

| 脚本 | 用途 | 强制 |
|------|------|------|
| `guide.py` | 状态诊断 + 下一步引导 | 每次触发先跑 |
| `new_novel.py` | 创建新小说 + 设为当前 | — |
| `list_novels.py` | 列出所有 + 切换当前 | — |
| `init_chapter.py` | 生成 PRE-FLIGHT + 章节草稿 | — |
| `validate_preflight.py` | 🆕 PRE-FLIGHT 强制验证 | **写正文前必须通过** |
| `init_character.py` | 创建人物档案 | — |
| `new_arc.py` | 按需生成新卷大纲 | — |
| `check_consistency.py` | 5 项一致性检查（含人物弧线） | 每卷/每10章 |
| `update_suspense.py` | 交互式悬念追踪 | 每章写完后 |

---

## 关键原则

1. **故事圣经 = 唯一权威**
2. **终点不可擅改**（核心事件 + 弧线终点需用户确认）
3. **悬念永不过期**（必须有回收计划，超 10 章报警）
4. **PRE-FLIGHT 不可跳过**（validate_preflight.py 是硬约束）
5. **人物弧线不可遗忘**（check_consistency.py 检测 10 章以上未更新的人物）
6. **参考文档按触发条件加载**（不用等用户主动提）
7. **用户有最终决定权**

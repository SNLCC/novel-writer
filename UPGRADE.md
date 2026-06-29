# 升级指南

## 安全架构

skill 目录与用户数据**物理隔离**，更新不会影响用户创作成果：

> **v1.1.0 重要更新**：所有脚本现在自动探测项目根目录（通过 `.reasonix` / `.git` 标记），stories 数据默认写入可写的工作区，而非 skill 自身的只读路径。可通过 `--path` 参数或 `CODEX_STORIES_PATH` 环境变量覆盖。

```
skill 目录（更新时完全替换）          用户数据（永不触碰）
├── scripts/                          stories/
├── references/                       ├── .shared/          ← 积累的知识库
├── assets/                           │   ├── pattern-library.md
├── SKILL.md                          │   └── platform-data.md
└── README.md                         ├── master-index.md   ← 项目索引
                                      ├── <小说A>/          ← 小说项目
                                      └── <小说B>/
`

## 更新方法

在 Codex 对话中输入：

`
/install-skill https://github.com/SNLCC/novel-writer
`

## 更新后验证

更新完成后运行：

`ash
python scripts/guide.py
`

如果一切正常，会显示你之前的小说项目状态。

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| 1.0.0 | 2026-06 | 初始发布：18 脚本，7 大系统 |

## 注意事项

- 更新前建议 git 备份 stories/ 目录
- .current-novel 文件可能需重新设置：python scripts/list_novels.py --set <小说名>
- stories/.shared/ 中的积累数据完全不受更新影响

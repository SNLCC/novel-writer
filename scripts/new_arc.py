#!/usr/bin/env python3
"""
new_arc.py — 按需创建新卷大纲

用法:
    python new_arc.py <卷号> --novel <小说目录>

从已有的 arc-01.md（或最新 arc）复制骨架，交互式填入卷信息。

示例:
    python new_arc.py 2 --novel ./stories/我的小说
    python new_arc.py 3 --novel ./stories/我的小说 --title "风云变幻"
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime

from _utils import resolve_novel_path


# ── 路径解析 ────────────────────────────────────────────────
# resolve_novel_path 已由 _utils 模块统一管理


def create_arc(novel_path: Path, arc_num: int, title: str | None):
    outline_dir = novel_path / "outline"
    outline_dir.mkdir(exist_ok=True)

    arc_filename = f"arc-{arc_num:02d}.md"
    arc_file = outline_dir / arc_filename

    if arc_file.exists():
        print(f"[WARN] {arc_filename} 已存在")
        ans = input("  覆盖？(y/N): ").strip().lower()
        if ans != 'y':
            print("  已取消。")
            return

    # 从已有 arc 中找模板（优先 arc-01，否则最新）
    existing = sorted(outline_dir.glob("arc-*.md"))
    template_file = existing[0] if existing else None

    if template_file:
        content = template_file.read_text(encoding="utf-8")
    else:
        # 回退到内置骨架
        content = f"""# 第{arc_num}卷大纲（Arc {arc_num:02d}）

> 📌 **本卷核心任务**：[一句话概括本卷要达成什么]

---

## 一、本卷章节列表

| 章 | 标题 | 钩子类型 | 核心冲突 | 字数 | 状态 |
|----|------|----------|----------|------|------|
|   |      |          |          |      | ⬜ |

---

## 二、每章细纲

（按 ch-XX 格式逐章展开）

---

## 三、本卷悬念清单

| 编号 | 悬念内容 | 埋设章 | 计划回收章 | 状态 |
|------|----------|--------|------------|------|
|      |          |        |            | 🔴 |
"""

    # 替换卷号和标题占位符
    vol_title = title or f"第{arc_num}卷"
    content = re.sub(r'第[一二三四五六七八九十\d]+卷', vol_title, content)
    content = re.sub(r'Arc \d+', f'Arc {arc_num:02d}', content)
    content = re.sub(r'arc-\d+', arc_filename, content)
    # 清空具体章节数据（保留表格结构但清除占位数据行）
    content = re.sub(r'S\d+-\d+', f'S{arc_num:02d}-XX', content)

    arc_file.write_text(content, encoding="utf-8")
    print(f"[OK] 创建卷大纲: {arc_file}")
    print(f"  卷号: {arc_num}")
    print(f"  标题: {vol_title}")
    print(f"\n✅ 请编辑 {arc_filename} 填写本卷章节规划和悬念清单。")
    print(f"  同时更新 outline/master.md 的本卷核心任务。")


def main():
    parser = argparse.ArgumentParser(description="创建新卷大纲")
    parser.add_argument("arc", type=int, help="卷号（如 2, 3, 4）")
    parser.add_argument("--novel", default=None, help="小说项目目录")
    parser.add_argument("--title", default=None, help="卷标题（可选）")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)

    if not (novel_path / "story-bible.md").exists():
        print(f"[WARN] 未找到 story-bible.md，继续创建但请确认目录正确")

    create_arc(novel_path, args.arc, args.title)


if __name__ == "__main__":
    main()

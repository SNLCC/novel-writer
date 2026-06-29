#!/usr/bin/env python3
"""
new_novel.py — 创建新小说项目骨架

用法:
    python new_novel.py <小说名> [--path <stories目录>] [--template <模板路径>]

创建后自动将新项目设为 .current-novel（当前小说）。

默认 stories 目录自动探测到项目根目录，不再固定在 ./stories。
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime
import re

from _utils import resolve_stories_root, get_template_path


def normalize_name(name: str) -> str:
    dangerous = '<>:"/\\|?*'
    result = name.strip()
    for ch in dangerous:
        result = result.replace(ch, '-')
    while '  ' in result:
        result = result.replace('  ', ' ')
    return result or 'untitled'


def sync_master_index(stories_path: Path, novel_name: str):
    index_file = stories_path / "master-index.md"
    today = datetime.now().strftime("%Y-%m-%d")
    novels = sorted([d for d in stories_path.iterdir()
                     if d.is_dir() and not d.name.startswith(".")])
    rows = []
    for i, nd in enumerate(novels, 1):
        meta_file = nd / "meta.md"
        meta = {}
        if meta_file.exists():
            text = meta_file.read_text(encoding="utf-8")
            for key, pat in [("type", r'\*\*类型\*\*\s*\|\s*(.+)'),
                              ("status", r'\*\*状态\*\*\s*\|\s*(.+)'),
                              ("updated", r'\*\*最后更新\*\*\s*\|\s*(.+)'),
                              ("created", r'\*\*创建日期\*\*\s*\|\s*(.+)')]:
                m = re.search(pat, text)
                if m:
                    meta[key] = m.group(1).strip()
        completed = 0
        ch_dir = nd / "chapters"
        if ch_dir.exists():
            for cf in ch_dir.glob("ch-*.md"):
                if "已完成" in cf.read_text(encoding="utf-8"):
                    completed += 1
        total_ch = len(list(ch_dir.glob("ch-*.md"))) if ch_dir.exists() else 0
        rows.append(
            f"| {i} | {nd.name} | {meta.get('type', '?')} | {meta.get('status', '?')} "
            f"| {completed} | {total_ch} | {meta.get('created', '?')} "
            f"| {meta.get('updated', '?')} | {nd.name}/ |"
        )
    total_n = len(novels)
    new_content = "# 📚 小说项目总索引\n\n"
    new_content += f"> **当前小说**：{novel_name}\n"
    new_content += f"> **最后更新**：{today}\n\n"
    new_content += "---\n\n## 项目列表\n\n"
    new_content += "| # | 书名 | 类型 | 状态 | 已完成章 | 总章数 | 创建日期 | 最后更新 | 路径 |\n"
    new_content += "|---|------|------|------|----------|--------|----------|----------|------|\n"
    new_content += "\n".join(rows) if rows else "|   |      |      |      |          |        |          |          |      |"
    new_content += "\n\n---\n\n## 跨项目统计\n\n"
    new_content += "| 指标 | 数值 |\n|------|------|\n"
    new_content += f"| **总项目数** | {total_n} |\n"
    new_content += "| **连载中** | — |\n"
    new_content += "| **已完结** | — |\n"
    new_content += "| **累计章节数** | — |\n"
    new_content += "| **累计字数（估）** | — |\n"
    index_file.write_text(new_content, encoding="utf-8")


def create_novel(novel_name: str, stories_path: Path, template_path: Path) -> Path:
    dir_name = normalize_name(novel_name)
    target = stories_path / dir_name

    if target.exists():
        print(f"[ERROR] 小说目录已存在: {target}")
        sys.exit(1)

    if not template_path.exists():
        print(f"[ERROR] 模板目录不存在: {template_path}")
        print("  确保 skill 的 assets/novel-template/ 目录完整")
        sys.exit(1)

    shutil.copytree(template_path, target)
    print(f"[OK] 创建小说目录: {target}")

    meta_file = target / "meta.md"
    today = datetime.now().strftime("%Y-%m-%d")
    if meta_file.exists():
        content = meta_file.read_text(encoding="utf-8")
        content = content.replace("[待定]", novel_name, 1)
        content = content.replace("[YYYY-MM-DD]", today, 2)
        meta_file.write_text(content, encoding="utf-8")
        print("[OK] 已初始化 meta.md")

    # 设置 .current-novel 指针
    pointer_file = stories_path / ".current-novel"
    pointer_file.write_text(str(target.resolve()), encoding="utf-8")
    print(f"[OK] 已设为当前小说: {target.name}")

    # 同步 master-index.md
    sync_master_index(stories_path, novel_name)

    print("\n项目结构：")
    for f in sorted(target.rglob("*")):
        if f.is_file():
            rel = f.relative_to(target)
            print(f"  {rel}")

    print(f"\n小说「{novel_name}」创建完成！")
    print(f"  路径: {target}")
    print("\n下一步：")
    print("  1. 编辑 story-bible.md — 设定世界观和规则")
    print("  2. 编辑 outline/master.md — 规划全书大纲和人物弧线")
    print("  3. 编辑 outline/arc-01.md — 规划第一卷章节大纲")
    print("  4. 运行 init_character.py 创建人物档案")
    print("  5. 运行 init_scene.py 创建场景档案")
    print("  6. 需要新卷时运行 new_arc.py")
    print("  7. 写章节时冒出新设定 → 运行 append_bible.py 追加到圣经")

    return target


def main():
    parser = argparse.ArgumentParser(description="创建新小说项目骨架")
    parser.add_argument("name", help="小说名称")
    parser.add_argument("--path", default=None, help="stories 目录路径（默认自动探测到项目根目录）")
    parser.add_argument("--template", default=None, help="模板路径（默认自动查找）")
    args = parser.parse_args()

    stories_path = resolve_stories_root(args.path)
    stories_path.mkdir(parents=True, exist_ok=True)
    template_path = get_template_path(args.template)

    create_novel(args.name, stories_path, template_path)


if __name__ == "__main__":
    main()

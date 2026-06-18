#!/usr/bin/env python3
"""
new_novel.py — 创建新小说项目骨架

用法:
    python new_novel.py <小说名> [--path <stories目录>] [--template <模板路径>]

创建后自动将新项目设为 .current-novel（当前小说）。
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime


def normalize_name(name: str) -> str:
    dangerous = '<>:"/\\|?*'
    result = name.strip()
    for ch in dangerous:
        result = result.replace(ch, '-')
    while '  ' in result:
        result = result.replace('  ', ' ')
    return result or 'untitled'


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
    print("  5. 需要新卷时运行 new_arc.py")

    return target


def main():
    parser = argparse.ArgumentParser(description="创建新小说项目骨架")
    parser.add_argument("name", help="小说名称")
    parser.add_argument("--path", default="./stories", help="stories 目录路径（默认 ./stories）")
    parser.add_argument("--template", default=None, help="模板路径（默认自动查找）")
    args = parser.parse_args()

    stories_path = Path(args.path).resolve()
    stories_path.mkdir(parents=True, exist_ok=True)

    if args.template:
        template_path = Path(args.template).resolve()
    else:
        script_dir = Path(__file__).resolve().parent
        template_path = script_dir.parent / "assets" / "novel-template"

    create_novel(args.name, stories_path, template_path)


if __name__ == "__main__":
    main()

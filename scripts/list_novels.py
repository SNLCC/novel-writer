#!/usr/bin/env python3
"""
list_novels.py — 列出所有小说项目及其状态

用法:
    python list_novels.py [--path <stories目录>] [--set <小说名>]

--set 将指定小说设为「当前小说」（写入 .current-novel）。
"""

import argparse
import re
from pathlib import Path


def parse_meta(meta_file: Path) -> dict:
    info = {
        "title": meta_file.parent.name,
        "type": "?",
        "status": "?",
        "chapters": "?",
        "updated": "?",
    }
    if not meta_file.exists():
        return info
    text = meta_file.read_text(encoding="utf-8")
    patterns = {
        "title": r'\*\*书名\*\*\s*\|\s*(.+)',
        "type": r'\*\*类型\*\*\s*\|\s*(.+)',
        "status": r'\*\*状态\*\*\s*\|\s*(.+)',
        "chapters": r'\*\*当前章节\*\*\s*\|\s*(.+)',
        "updated": r'\*\*最后更新\*\*\s*\|\s*(.+)',
    }
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            info[key] = m.group(1).strip()
    return info


def count_completed_chapters(chapters_dir: Path) -> int:
    if not chapters_dir.exists():
        return 0
    count = 0
    for f in chapters_dir.glob("ch-*.md"):
        content = f.read_text(encoding="utf-8")
        if "已完成" in content:
            count += 1
    return count


def get_current_novel(stories_path: Path) -> str | None:
    pointer = stories_path / ".current-novel"
    if pointer.exists():
        target = pointer.read_text(encoding="utf-8").strip()
        return Path(target).name
    return None


def set_current_novel(stories_path: Path, novel_name: str):
    target = stories_path / novel_name
    if not target.exists():
        print(f"[ERROR] 小说目录不存在: {target}")
        return
    pointer = stories_path / ".current-novel"
    pointer.write_text(str(target.resolve()), encoding="utf-8")
    print(f"[OK] 当前小说已设为: {novel_name}")


def list_novels(stories_path: Path):
    if not stories_path.exists():
        print(f"[INFO] stories 目录尚不存在: {stories_path}")
        print("  运行 new_novel.py 创建第一部小说吧。")
        return

    novels = sorted([d for d in stories_path.iterdir()
                     if d.is_dir() and not d.name.startswith(".")])

    if not novels:
        print(f"[INFO] {stories_path} 下还没有小说项目。")
        return

    current = get_current_novel(stories_path)

    print(f"{'':>2} {'书名':<18} {'类型':<14} {'状态':<10} {'已完成':<6} {'最后更新':<12}")
    print("-" * 72)

    for novel_dir in novels:
        meta = parse_meta(novel_dir / "meta.md")
        completed = count_completed_chapters(novel_dir / "chapters")
        marker = "> " if novel_dir.name == current else "  "

        title = meta["title"][:16]
        ntype = meta["type"][:12]
        status = meta["status"][:8]
        updated = meta["updated"][:10]

        print(f"{marker} {title:<18} {ntype:<14} {status:<10} {completed:<6} {updated:<12}")

    print("-" * 72)
    print(f"共 {len(novels)} 部小说  |  > = 当前小说")
    if not current:
        print("  提示：python list_novels.py --set <小说名> 设置当前小说")


def main():
    parser = argparse.ArgumentParser(description="列出所有小说项目")
    parser.add_argument("--path", default="./stories", help="stories 目录路径（默认 ./stories）")
    parser.add_argument("--set", default=None, help="设为当前小说", metavar="NOVEL_NAME")
    args = parser.parse_args()

    stories_path = Path(args.path).resolve()

    if args.set:
        set_current_novel(stories_path, args.set)
        print()

    list_novels(stories_path)


if __name__ == "__main__":
    main()

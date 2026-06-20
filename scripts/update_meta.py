#!/usr/bin/env python3
"""
update_meta.py — 自动更新元信息和故事时间线

用法:
    python update_meta.py [--novel <小说目录>]

功能：
    1. 扫描所有章节，更新 meta.md 的当前章节数、状态、最后更新日期
    2. 从各章「写后归档」提取摘要，汇聚到 meta.md
    3. 从各章提取时间信息，更新 timeline.md

建议每写完一章或每5章运行一次，保持元信息同步。
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime


def resolve_novel_path(explicit_path):
    if explicit_path:
        novel_path = Path(explicit_path).resolve()
        if novel_path.exists():
            return novel_path
        print(f"[ERROR] 目录不存在: {novel_path}")
        sys.exit(1)
    current_dir = Path.cwd()
    pointer_file = current_dir / ".current-novel"
    if pointer_file.exists():
        target = pointer_file.read_text(encoding="utf-8").strip()
        novel_path = Path(target)
        if novel_path.exists():
            return novel_path.resolve()
    return current_dir


def scan_chapters(novel_path):
    """扫描所有章节，返回章节信息列表"""
    chapters_dir = novel_path / "chapters"
    if not chapters_dir.exists():
        return []

    chapters = []
    for cf in sorted(chapters_dir.glob("ch-*.md")):
        text = cf.read_text(encoding="utf-8")
        ch_num = int(re.search(r'ch-(\d+)', cf.name).group(1))

        info = {
            "file": cf,
            "number": ch_num,
            "completed": "已完成" in text or "✅" in text,
            "title": f"第{ch_num}章",
            "summary": "",
            "new_settings": [],
            "character_changes": [],
            "scene_changes": [],
            "timeline_events": [],
        }

        # 提取标题
        title_match = re.search(r'^#\s*(.+)', text, re.MULTILINE)
        if title_match:
            info["title"] = title_match.group(1).strip()

        # 提取摘要
        summary_section = extract_section(text, "本章摘要", "新设定")
        if summary_section:
            lines = [l.strip() for l in summary_section.split("\n")
                     if l.strip() and not l.strip().startswith("[")]
            info["summary"] = " ".join(lines)[:200]

        # 提取新设定
        settings_section = extract_section(text, "新设定", "人物变化")
        if settings_section:
            for line in settings_section.split("\n"):
                m = re.match(r'-\s*(.+)', line.strip())
                if m and m.group(1) and not m.group(1).startswith("["):
                    info["new_settings"].append(m.group(1)[:80])

        # 提取人物变化
        char_section = extract_section(text, "人物变化", "场景变化")
        if not char_section:
            char_section = extract_section(text, "人物变化", "悬念追踪")
        if char_section:
            for line in char_section.split("\n"):
                m = re.match(r'-\s*(.+)', line.strip())
                if m and m.group(1) and not m.group(1).startswith("["):
                    info["character_changes"].append(m.group(1)[:80])

        # 提取场景变化
        scene_section = extract_section(text, "场景变化", "悬念追踪")
        if scene_section:
            for line in scene_section.split("\n"):
                m = re.match(r'-\s*(.+)', line.strip())
                if m and m.group(1) and not m.group(1).startswith("["):
                    info["scene_changes"].append(m.group(1)[:80])

        # 提取时间线事件
        timeline_section = extract_section(text, "悬念追踪", "钩子执行")
        if not timeline_section:
            fallback = extract_section(text, "悬念追踪", None)
            if fallback:
                timeline_section = fallback[:300]
        # Look for time references in the body
        body = extract_section(text, "正文", "写后归档")
        if body:
            time_refs = re.findall(r'(?:第[一二三四五六七八九十\d]+天|[一二三四五六七八九十\d]+天后|次日|当天|翌日|数月后|数年后|三年后|十年后|[\d]+年前)', body)
            info["timeline_events"] = time_refs[:5]

        chapters.append(info)

    return chapters


def extract_section(text, start_marker, end_marker):
    """提取两个标记之间的文本"""
    start_idx = text.find(start_marker)
    if start_idx == -1:
        return ""
    start_idx = text.find("\n", start_idx)
    if start_idx == -1:
        return ""

    if end_marker:
        end_idx = text.find(end_marker, start_idx)
        if end_idx == -1:
            end_idx = len(text)
    else:
        end_idx = len(text)

    return text[start_idx:end_idx].strip()


def update_meta(novel_path, chapters):
    """更新 meta.md"""
    meta_file = novel_path / "meta.md"
    if not meta_file.exists():
        print("[WARN] meta.md 不存在，跳过")
        return

    text = meta_file.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    completed = sum(1 for ch in chapters if ch["completed"])
    total = len(chapters)

    # 判断状态
    if total == 0:
        status = "🟡 筹备中"
    elif completed == total and total > 0:
        status = "⚪ 已完结"
    else:
        status = "🟢 连载中"

    # 替换关键字段
    text = re.sub(r'\*\*当前章节\*\*\s*\|\s*[\d]+', f'**当前章节** | {total}', text)
    text = re.sub(r'\*\*最后更新\*\*\s*\|\s*\[[^\]]+\]', f'**最后更新** | {today}', text)
    text = re.sub(r'\*\*状态\*\*\s*\|\s*.+', f'**状态** | {status}', text)

    # 追加章节摘要汇总
    summary_header = "\n## 章节摘要汇总\n\n"
    if summary_header in text:
        text = text[:text.find(summary_header)]

    if chapters:
        summary_lines = [summary_header]
        summary_lines.append("| 章 | 标题 | 状态 | 摘要 |")
        summary_lines.append("|----|------|------|------|")
        for ch in chapters:
            status_mark = "✅" if ch["completed"] else "⬜"
            summ = ch["summary"][:60] if ch["summary"] else "—"
            title_short = ch["title"].replace("|", "/")[:20]
            summary_lines.append(f"| ch-{ch['number']:02d} | {title_short} | {status_mark} | {summ} |")

        text += "\n".join(summary_lines) + "\n"

    meta_file.write_text(text, encoding="utf-8")
    print(f"[OK] meta.md 已更新")
    print(f"  总章节: {total}  |  已完成: {completed}  |  状态: {status}")


def update_timeline(novel_path, chapters):
    """更新 timeline.md"""
    timeline_file = novel_path / "timeline.md"
    if not timeline_file.exists():
        print("[WARN] timeline.md 不存在，跳过")
        return

    text = timeline_file.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")

    # 找到表格末尾，追加新条目
    table_header = "| 故事时间 | 对应章节 | 关键事件 | 涉及人物 |"
    table_start = text.find(table_header)
    if table_start == -1:
        print("[WARN] timeline.md 格式异常，跳过")
        return

    # 提取已有的章节条目
    existing_chapters = set()
    for m in re.finditer(r'\|\s*(?:ch-)?(\d+)\s*\|', text):
        existing_chapters.add(int(m.group(1)))

    # 找表格结束位置（下一个 ## 标题之前）
    after_table = text.find("\n##", table_start + len(table_header))
    if after_table == -1:
        after_table = len(text)

    new_rows = []
    for ch in chapters:
        if ch["number"] in existing_chapters:
            continue
        if not ch["completed"]:
            continue

        # 构建时间信息
        time_info = "—"
        if ch["timeline_events"]:
            time_info = ch["timeline_events"][0]

        # 构建事件描述
        events = ch["summary"][:60] if ch["summary"] else "—"

        new_rows.append(f"| {time_info} | ch-{ch['number']:02d} | {events} | — |")

    if new_rows:
        insert_pos = after_table
        lines = text.split("\n")
        lines.insert(insert_pos, "\n".join(new_rows))
        text = "\n".join(lines)
        timeline_file.write_text(text, encoding="utf-8")
        print(f"[OK] timeline.md 新增 {len(new_rows)} 条记录")
    else:
        print(f"[OK] timeline.md 无需更新（所有章节已记录）")


def main():
    parser = argparse.ArgumentParser(description="自动更新元信息和故事时间线")
    parser.add_argument("--novel", default=None, help="小说项目目录")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)
    if not novel_path:
        print("[ERROR] 无法定位小说项目。")
        sys.exit(1)

    chapters = scan_chapters(novel_path)

    if not chapters:
        print("[INFO] 尚无章节文件")
        return

    print(f"\n扫描到 {len(chapters)} 个章节（已完成 {sum(1 for c in chapters if c['completed'])} 个）\n")

    update_meta(novel_path, chapters)
    update_timeline(novel_path, chapters)

    # 汇总
    print(f"\n{'='*50}")
    print(f"更新汇总")
    print(f"  章节总数: {len(chapters)}")
    print(f"  已完成: {sum(1 for c in chapters if c['completed'])}")

    # 检查是否有未填摘要的已完成章节
    no_summary = [c for c in chapters if c["completed"] and not c["summary"]]
    if no_summary:
        print(f"  ⚠️ {len(no_summary)} 个已完成章节缺少摘要：")
        for c in no_summary[:5]:
            print(f"     ch-{c['number']:02d}")

    print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
track_clue.py — 线索/悬念/伏笔统一管理

用法:
    # 添加条目
    python track_clue.py add --type 悬念 --content "<内容>" --planted 5 --planned 20 [--novel <目录>]

    # 列出条目（可按类型过滤）
    python track_clue.py list [--type 悬念|线索|伏笔] [--status 未回收|已回收] [--novel <目录>]

    # 检查线索链完整性
    python track_clue.py check [--novel <目录>]

    # 获取某章需处理的条目
    python track_clue.py pending --chapter 10 [--novel <目录>]

    # 标记条目状态
    python track_clue.py resolve <编号> --chapter <实际章> [--novel <目录>]
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime


# ── 路径解析 ────────────────────────────────────────────────

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


# ── 解析 ────────────────────────────────────────────────────

def parse_entries(content):
    """解析追踪表中的所有条目"""
    entries = []
    current_volume = None
    header_keywords = {"编号", "类型", "悬念内容", "内容", "埋设章"}

    for line in content.split("\n"):
        # 检测卷标题
        vol_match = re.match(r'##\s*(第[一二三四五六七八九十\d]+卷)', line)
        if vol_match:
            current_volume = vol_match.group(1)
            continue

        # 跳过表头和分隔
        if any(kw in line for kw in header_keywords):
            continue
        if "---" in line or not line.strip():
            continue
        if "|" not in line:
            continue
        if line.strip().startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 7:
            continue

        # 跳过占位行
        if parts[1] in ("[类型]", "类型"):
            continue
        content_val = parts[2] if len(parts) > 2 else ""
        if content_val.startswith("[") and content_val.endswith("]"):
            continue

        entry = {
            "id": parts[0],
            "type": parts[1] if len(parts) > 1 else "?",
            "content": parts[2] if len(parts) > 2 else "",
            "planted": parts[3] if len(parts) > 3 else "",
            "planned": parts[4] if len(parts) > 4 else "",
            "actual": parts[5] if len(parts) > 5 else "—",
            "status": parts[6] if len(parts) > 6 else "?",
            "character": parts[7] if len(parts) > 7 else "",
            "linked_suspense": parts[8] if len(parts) > 8 else "",
            "volume": current_volume or "未知",
            "raw_line": line,
        }
        entries.append(entry)

    return entries


def get_tracking_file(novel_path):
    return novel_path / "notes" / "suspense-tracking.md"


# ── 命令：add ────────────────────────────────────────────────

def cmd_add(novel_path, entry_type, content, planted, planned, character, linked):
    tf = get_tracking_file(novel_path)
    if not tf.exists():
        print("[ERROR] 线索追踪表不存在")
        print("  请先初始化小说项目。")
        sys.exit(1)

    file_text = tf.read_text(encoding="utf-8")

    # 查找第一卷表格
    vol1_match = re.search(r'(## 第一卷\n.*?)(\n## |\n---\n## |$)', file_text, re.DOTALL)
    if not vol1_match:
        print("[ERROR] 未找到第一卷表格")
        sys.exit(1)

    # 生成编号
    entries = parse_entries(file_text)
    vol1_entries = [e for e in entries if "第一" in e["volume"]]
    max_id = 0
    for e in vol1_entries:
        m = re.search(r'S(\d+)', e["id"])
        if m:
            max_id = max(max_id, int(m.group(1)))

    new_id = f"S{max_id + 1:02d}" if max_id > 0 else "S01"
    ch_str = f"ch-{int(planted):02d}"
    plan_str = f"ch-{int(planned):02d}"

    new_row = (
        f"| {new_id} | {entry_type} | {content} | {ch_str} "
        f"| {plan_str} | — | 未回收 | {character or '—'} | {linked or '—'} |"
    )

    # 插入到第一卷表格末尾
    lines = file_text.split("\n")
    vol1_section_end = None
    in_vol1 = False
    for i, line in enumerate(lines):
        if line.strip().startswith("## 第一卷"):
            in_vol1 = True
            continue
        if in_vol1 and line.strip().startswith("##"):
            vol1_section_end = i
            break

    if vol1_section_end is None:
        vol1_section_end = len(lines)

    # 在表格最后一行后面插入
    insert_at = vol1_section_end
    for j in range(vol1_section_end - 1, 0, -1):
        if lines[j].strip().startswith("|"):
            insert_at = j + 1
            break

    lines.insert(insert_at, new_row)
    tf.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ 已添加 [{new_id}] {entry_type}：{content}")
    print(f"   埋设: {ch_str}  |  计划揭示: {plan_str}")


# ── 命令：list ───────────────────────────────────────────────

def cmd_list(novel_path, entry_type, status_filter):
    tf = get_tracking_file(novel_path)
    if not tf.exists():
        print("[INFO] 线索追踪表不存在")
        return

    entries = parse_entries(tf.read_text(encoding="utf-8"))
    if not entries:
        print("[INFO] 暂无条目")
        return

    if entry_type:
        entries = [e for e in entries if e["type"] == entry_type]
    if status_filter:
        entries = [e for e in entries if status_filter in e["status"]]

    type_order = {"悬念": 0, "线索": 1, "伏笔": 2}
    entries.sort(key=lambda e: type_order.get(e["type"], 9))

    print(f"\n{'编号':<6} {'类型':<6} {'内容':<36} {'埋设':<6} {'计划':<6} {'实际':<6} {'状态':<8}")
    print("-" * 80)
    for e in entries:
        content = e["content"][:34]
        print(f"{e['id']:<6} {e['type']:<6} {content:<36} {e['planted']:<6} {e['planned']:<6} {e['actual']:<6} {e['status']:<8}")

    suspense_count = sum(1 for e in entries if e["type"] == "悬念")
    clue_count = sum(1 for e in entries if e["type"] == "线索")
    foreshadow_count = sum(1 for e in entries if e["type"] == "伏笔")
    unresolved = sum(1 for e in entries if "未回收" in e["status"])
    print(f"\n悬念 {suspense_count}  |  线索 {clue_count}  |  伏笔 {foreshadow_count}  |  未回收 {unresolved}")


# ── 命令：check ──────────────────────────────────────────────

def cmd_check(novel_path):
    tf = get_tracking_file(novel_path)
    if not tf.exists():
        print("[INFO] 线索追踪表不存在")
        return

    entries = parse_entries(tf.read_text(encoding="utf-8"))
    if not entries:
        print("[INFO] 暂无条目")
        return

    issues = []

    # 1. 检查孤儿条目
    for e in entries:
        if "已回收" in e["status"] or "已揭示" in e["status"]:
            continue
        m = re.search(r'(\d+)', e["planned"])
        if m:
            planned = int(m.group(1))
            chapters_dir = novel_path / "chapters"
            if chapters_dir.exists():
                max_ch = len(list(chapters_dir.glob("ch-*.md")))
                overdue = max_ch - planned
                if overdue > 10:
                    issues.append({
                        "severity": "error",
                        "title": f"孤儿条目 [{e['id']}] {e['type']}",
                        "detail": f"{e['content'][:40]} — 超期 {overdue} 章未处理",
                    })
                elif overdue > 5:
                    issues.append({
                        "severity": "warning",
                        "title": f"即将过期 [{e['id']}] {e['type']}",
                        "detail": f"{e['content'][:40]} — 超期 {overdue} 章",
                    })

    # 2. 检查线索链
    suspense_entries = [e for e in entries if e["type"] == "悬念"]
    clue_entries = [e for e in entries if e["type"] == "线索"]

    for s in suspense_entries:
        linked = [c for c in clue_entries if s["id"] in (c.get("linked_suspense") or "")]
        if not linked and "已回收" not in s["status"]:
            issues.append({
                "severity": "info",
                "title": f"悬念 [{s['id']}] 无关联线索",
                "detail": f"{s['content'][:40]} — 建议补充线索链",
            })

    # 3. 伏笔是否指向明确的悬念
    foreshadow_entries = [e for e in entries if e["type"] == "伏笔"]
    orphan_foreshadows = [f for f in foreshadow_entries if not f.get("linked_suspense") or f["linked_suspense"] == "—"]
    if orphan_foreshadows:
        issues.append({
            "severity": "info",
            "title": f"{len(orphan_foreshadows)} 个伏笔未关联悬念",
            "detail": "伏笔应指向一个具体悬念，确保有回收计划",
        })

    # 输出
    if not issues:
        print("\n✅ 线索追踪检查通过！")
        print(f"   共 {len(entries)} 个条目（悬念 {sum(1 for e in entries if e['type']=='悬念')} / 线索 {sum(1 for e in entries if e['type']=='线索')} / 伏笔 {sum(1 for e in entries if e['type']=='伏笔')}）")
        return

    severity_order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: severity_order.get(i["severity"], 5))

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warn_count = sum(1 for i in issues if i["severity"] == "warning")

    print(f"\n线索追踪检查 — {novel_path.name}\n")
    for issue in issues:
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue["severity"], "•")
        print(f"  {icon} {issue['title']}")
        print(f"     {issue['detail']}")

    print(f"\n共 {error_count} 个错误，{warn_count} 个警告")
    if error_count > 0:
        sys.exit(1)


# ── 命令：pending ────────────────────────────────────────────

def cmd_pending(novel_path, chapter_num):
    tf = get_tracking_file(novel_path)
    if not tf.exists():
        print("[INFO] 线索追踪表不存在")
        return

    entries = parse_entries(tf.read_text(encoding="utf-8"))
    pending = []
    for e in entries:
        if "已回收" in e["status"] or "已揭示" in e["status"]:
            continue
        m = re.search(r'(\d+)', e["planned"])
        if m:
            plan_num = int(m.group(1))
            if plan_num <= chapter_num:
                pending.append(e)

    if not pending:
        print(f"\n第 {chapter_num} 章无需处理的线索/悬念/伏笔。")
        return

    print(f"\n第 {chapter_num} 章需处理的条目：\n")
    for e in pending:
        overdue = chapter_num - int(re.search(r'(\d+)', e["planned"]).group(1))
        tag = "⚠️ 超期" if overdue > 5 else ""
        print(f"  [{e['id']}] {e['type']}: {e['content'][:50]} {tag}")
        print(f"     计划揭示: {e['planned']}  |  关联: {e.get('linked_suspense', '—')}")

    print(f"\n共 {len(pending)} 个待处理条目")


# ── 命令：resolve ────────────────────────────────────────────

def cmd_resolve(novel_path, entry_id, chapter_num):
    tf = get_tracking_file(novel_path)
    if not tf.exists():
        print("[ERROR] 线索追踪表不存在")
        sys.exit(1)

    content = tf.read_text(encoding="utf-8")
    ch_str = f"ch-{chapter_num:02d}"

    found = False
    new_lines = []
    for line in content.split("\n"):
        if entry_id in line and "|" in line:
            parts = line.split("|")
            if len(parts) >= 7:
                parts[5] = f" {ch_str} "
                parts[6] = parts[6].replace("未回收", "已回收").replace("未揭示", "已揭示")
                line = "|".join(parts)
                found = True
        new_lines.append(line)

    if not found:
        print(f"[ERROR] 未找到条目: {entry_id}")
        sys.exit(1)

    tf.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"✅ 已标记 [{entry_id}] 为已处理（{ch_str}）")


# ── 主入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="线索/悬念/伏笔统一管理")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # add
    p_add = subparsers.add_parser("add", help="添加条目")
    p_add.add_argument("--type", required=True, choices=["悬念", "线索", "伏笔"])
    p_add.add_argument("--content", required=True, help="条目内容")
    p_add.add_argument("--planted", required=True, type=int, help="埋设章节号")
    p_add.add_argument("--planned", required=True, type=int, help="计划揭示章节号")
    p_add.add_argument("--character", default=None, help="关联人物")
    p_add.add_argument("--linked", default=None, help="关联悬念编号")
    p_add.add_argument("--novel", default=None)

    # list
    p_list = subparsers.add_parser("list", help="列出条目")
    p_list.add_argument("--type", default=None, choices=["悬念", "线索", "伏笔"])
    p_list.add_argument("--status", default=None, help="状态过滤")
    p_list.add_argument("--novel", default=None)

    # check
    p_check = subparsers.add_parser("check", help="检查完整性")
    p_check.add_argument("--novel", default=None)

    # pending
    p_pending = subparsers.add_parser("pending", help="获取待处理条目")
    p_pending.add_argument("--chapter", required=True, type=int)
    p_pending.add_argument("--novel", default=None)

    # resolve
    p_resolve = subparsers.add_parser("resolve", help="标记条目已处理")
    p_resolve.add_argument("id", help="条目编号")
    p_resolve.add_argument("--chapter", required=True, type=int, help="实际揭示章")
    p_resolve.add_argument("--novel", default=None)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    novel_path = resolve_novel_path(
        getattr(args, "novel", None)
    )

    if args.command == "add":
        cmd_add(novel_path, args.type, args.content, args.planted, args.planned,
                getattr(args, "character", None), getattr(args, "linked", None))
    elif args.command == "list":
        cmd_list(novel_path, getattr(args, "type", None), getattr(args, "status", None))
    elif args.command == "check":
        cmd_check(novel_path)
    elif args.command == "pending":
        cmd_pending(novel_path, args.chapter)
    elif args.command == "resolve":
        cmd_resolve(novel_path, args.id, args.chapter)


if __name__ == "__main__":
    main()

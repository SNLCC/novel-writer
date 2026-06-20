#!/usr/bin/env python3
"""
update_suspense.py — 交互式更新悬念追踪表

用法:
    python update_suspense.py --novel <小说目录> --chapter <章节号>

交互流程：
    1. 列出本章需回收的悬念（计划回收章 <= 当前章）
    2. 逐一确认是否已回收
    3. 添加新埋的悬念
    4. 更新 suspense-tracking.md
"""

import argparse
import re
import sys
from pathlib import Path


def resolve_novel_path(explicit_path):
    if explicit_path:
        n = Path(explicit_path).resolve()
        if n.exists():
            return n
        print(f"[ERROR] 目录不存在: {n}")
        sys.exit(1)
    cwd = Path.cwd()
    pf = cwd / ".current-novel"
    if pf.exists():
        n = Path(pf.read_text(encoding="utf-8").strip())
        if n.exists():
            return n.resolve()
    return cwd


def parse_suspense_entries(content):
    """解析悬念追踪表中的所有条目"""
    entries = []
    header_kw = {"编号", "悬念内容", "埋设章", "计划回收章", "状态"}
    for line in content.split("\n"):
        if any(kw in line for kw in header_kw):
            continue
        if "---" in line or not line.strip():
            continue
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]
        if len(parts) >= 6:
            entries.append({
                "id": parts[0],
                "content": parts[1],
                "planted": parts[2],
                "planned": parts[3],
                "actual": parts[4],
                "status": parts[5],
                "raw_line": line,
            })
    return entries


def get_pending(entries, chapter_num):
    """获取本章需回收的悬念"""
    pending = []
    for e in entries:
        if "已回收" in e["status"]:
            continue
        m = re.search(r'(\d+)', e["planned"])
        if m:
            plan_num = int(m.group(1))
            if plan_num <= chapter_num:
                pending.append(e)
    return pending


def update_suspense_file(novel_path, chapter_num):
    suspense_file = novel_path / "notes" / "suspense-tracking.md"

    if not suspense_file.exists():
        print("[ERROR] 悬念追踪表不存在")
        sys.exit(1)

    content = suspense_file.read_text(encoding="utf-8")
    entries = parse_suspense_entries(content)
    pending = get_pending(entries, chapter_num)
    ch_str = f"ch-{chapter_num:02d}"

    print(f"\n第 {chapter_num} 章悬念追踪更新\n")
    print(f"当前悬念总数: {len(entries)}")
    print(f"需回收悬念: {len(pending)}")

    # 步骤1：确认回收
    recovered_ids = set()
    if pending:
        print("\n--- 回收确认 ---")
        for e in pending:
            ans = input(f"  [{e['id']}] {e['content']} — 是否已回收？(y/N/q): ").strip().lower()
            if ans == 'q':
                print("  已退出。")
                return
            if ans == 'y':
                recovered_ids.add(e['id'])
                print(f"    标记为已回收")
            else:
                print(f"    保持未回收")

    # 步骤2：添加新悬念
    print("\n--- 新埋悬念 ---")
    new_entries = []
    while True:
        content_input = input("  新条目内容（空行结束）: ").strip()
        if not content_input:
            break
        entry_type = input("  类型？(1=悬念 2=线索 3=伏笔，默认1): ").strip()
        type_map = {"1": "悬念", "2": "线索", "3": "伏笔"}
        entry_type_str = type_map.get(entry_type, "悬念")
        plan_ch = input(f"  计划在第几章揭示/回收？(默认 {chapter_num + 10}): ").strip()
        if not plan_ch:
            plan_ch = str(chapter_num + 10)
        character = input("  关联人物（可选）: ").strip() or "—"
        linked = input("  关联悬念编号（可选）: ").strip() or "—"

        new_id = f"S{chapter_num:02d}-{len(new_entries) + 1:02d}"
        new_entries.append(
            f"| {new_id} | {entry_type_str} | {content_input} | {ch_str} "
            f"| ch-{int(plan_ch):02d} | — | 未回收 | {character} | {linked} |"
        )
        print(f"    已添加 [{new_id}] {entry_type_str}：{content_input}")
        print(f"    已添加 [{new_id}] {content_input}")

    # 步骤3：更新文件
    new_lines = []
    for line in content.split("\n"):
        updated = False
        for e in entries:
            if e["id"] in recovered_ids and e["id"] in line:
                line = line.replace("未回收", "已回收").replace("部分回收", "已回收").replace("未揭示", "已揭示")
                # 更新实际回收章
                parts = line.split("|")
                if len(parts) >= 6:
                    parts[4] = f" {ch_str} "
                    line = "|".join(parts)
                updated = True
                break
        new_lines.append(line)

    if new_entries:
        new_lines.append("")
        new_lines.extend(new_entries)

    suspense_file.write_text("\n".join(new_lines), encoding="utf-8")

    # 汇总
    print(f"\n{'='*50}")
    print(f"更新汇总")
    print(f"  已回收: {len(recovered_ids)} 个")
    print(f"  新埋: {len(new_entries)} 个")
    print(f"  仍待回收: {len(pending) - len(recovered_ids)} 个")
    print(f"\n悬念追踪表已更新: {suspense_file}")


def main():
    parser = argparse.ArgumentParser(description="更新悬念追踪表")
    parser.add_argument("--novel", default=None, help="小说项目目录")
    parser.add_argument("--chapter", type=int, required=True, help="当前章节号")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)
    update_suspense_file(novel_path, args.chapter)


if __name__ == "__main__":
    main()

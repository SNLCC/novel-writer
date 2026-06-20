#!/usr/bin/env python3
"""
sync_library.py — 从已完结小说中提取模式，同步到共享库

用法:
    python sync_library.py [--path <stories目录>] [--novel <小说名>]

功能：
    1. 扫描所有小说的章节数据
    2. 提取：钩子类型分布、平均章字数、爽点密度、节奏模式
    3. 对比跨项目数据，发现可复用的成功模式
    4. 将发现追加到 .shared/pattern-library.md
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime


def scan_novel(nd):
    """扫描单部小说的数据"""
    data = {
        "name": nd.name,
        "chapters": 0,
        "completed": 0,
        "hook_types": {},
        "total_chars": 0,
        "avg_chapter_chars": 0,
        "status": "?",
    }

    meta_file = nd / "meta.md"
    if meta_file.exists():
        text = meta_file.read_text(encoding="utf-8")
        m = re.search(r'\*\*状态\*\*\s*\|\s*(.+)', text)
        if m:
            data["status"] = m.group(1).strip()

    chapters_dir = nd / "chapters"
    if not chapters_dir.exists():
        return data

    chapter_files = sorted(chapters_dir.glob("ch-*.md"))
    data["chapters"] = len(chapter_files)

    for cf in chapter_files:
        text = cf.read_text(encoding="utf-8")
        if "已完成" in text:
            data["completed"] += 1

        # Extract hook type
        for hook_type in ["悬念", "反转", "情绪", "信息差", "悬念切割", "信息揭露", "冲突升级", "情感高点", "反向预期"]:
            if f"**{hook_type}**" in text or f"钩子类型确认：**{hook_type}**" in text:
                data["hook_types"][hook_type] = data["hook_types"].get(hook_type, 0) + 1

        # Count body chars
        body_start = text.find("## 正文")
        body_end = text.find("## 写后归档")
        if body_start != -1:
            body = text[body_start:body_end] if body_end != -1 else text[body_start:]
            body = re.sub(r'[\s\n#\-*>|]', '', body)
            data["total_chars"] += len(body)

    if data["chapters"] > 0:
        data["avg_chapter_chars"] = data["total_chars"] // data["chapters"]

    return data


def generate_insights(all_data):
    """基于跨项目数据生成洞察"""
    insights = []

    completed = [d for d in all_data if "完结" in d["status"] and d["completed"] > 0]
    if not completed:
        insights.append("暂无已完结小说，完成第一部小说后将有更多数据。")
        return insights

    # 1. 钩子类型分析
    all_hooks = {}
    for d in completed:
        for ht, count in d["hook_types"].items():
            all_hooks[ht] = all_hooks.get(ht, 0) + count

    if all_hooks:
        top_hooks = sorted(all_hooks.items(), key=lambda x: x[1], reverse=True)[:3]
        insight = "最常用钩子类型："
        insight += "、".join(f"{h}（{c}次）" for h, c in top_hooks)
        insight += "\n建议：确保钩子类型多样化，避免单一模式疲劳。"
        insights.append(insight)

    # 2. 章节字数分析
    avg_chars = [d["avg_chapter_chars"] for d in completed if d["avg_chapter_chars"] > 0]
    if avg_chars:
        overall_avg = sum(avg_chars) // len(avg_chars)
        insights.append(f"跨项目平均章字数：{overall_avg:,} 字。")

    # 3. 总字数统计
    total_all = sum(d["total_chars"] for d in completed)
    novel_count = len(completed)
    insights.append(f"已完成 {novel_count} 部小说，累计约 {total_all:,} 字。")

    # 4. 建议
    if novel_count >= 2:
        insights.append("建议对比各部的钩子分布，找出最适合目标平台的模式。")
    if novel_count >= 3:
        insights.append("已积累足够数据，建议提炼个人写作公式（开篇策略+节奏模板+钩子组合）。")

    return insights


def update_library(stories_path, all_data, insights):
    """更新共享库"""
    shared_dir = stories_path / ".shared"
    shared_dir.mkdir(exist_ok=True)
    lib_file = shared_dir / "pattern-library.md"

    today = datetime.now().strftime("%Y-%m-%d")

    if not lib_file.exists():
        # Create from template
        content = f"""# 📖 跨项目写作模式库

> 📌 **规则**：每完成一部小说或一个卷，复盘成果自动追加到本文档。
> **最后更新**：{today}

---

## 一、已验证的钩子模式

## 二、节奏配方

## 三、人物原型洞察

## 四、平台实战经验

## 五、常见问题与修复

## 六、复盘记录

## 七、自动分析记录

"""
        lib_file.write_text(content, encoding="utf-8")

    text = lib_file.read_text(encoding="utf-8")

    # Append auto-analysis section
    analysis = f"\n### {today} 自动分析\n\n"
    analysis += f"**分析范围**：{len(all_data)} 部小说\n\n"
    for insight in insights:
        analysis += f"- {insight}\n"

    # Add novel summary rows
    analysis += "\n| 小说 | 章节数 | 已完成 | 平均字数 | 状态 |\n"
    analysis += "|------|--------|--------|----------|------|\n"
    for d in all_data:
        analysis += f"| {d['name']} | {d['chapters']} | {d['completed']} | {d['avg_chapter_chars']:,} | {d['status']} |\n"

    if "## 七、自动分析记录" not in text:
        text += "\n---\n\n## 七、自动分析记录\n"
    text += analysis

    lib_file.write_text(text, encoding="utf-8")
    print(f"[OK] 共享库已更新: {lib_file}")


def main():
    parser = argparse.ArgumentParser(description="从已完结小说提取模式到共享库")
    parser.add_argument("--path", default="./stories", help="stories 目录路径")
    parser.add_argument("--novel", default=None, help="仅分析指定小说")
    args = parser.parse_args()

    stories_path = Path(args.path).resolve()
    if not stories_path.exists():
        print(f"[ERROR] stories 目录不存在: {stories_path}")
        sys.exit(1)

    novels = sorted([d for d in stories_path.iterdir()
                     if d.is_dir() and not d.name.startswith(".")])

    if args.novel:
        novels = [d for d in novels if d.name == args.novel]
        if not novels:
            print(f"[ERROR] 未找到小说: {args.novel}")
            sys.exit(1)

    if not novels:
        print("[INFO] 暂无小说项目")
        return

    all_data = [scan_novel(nd) for nd in novels]

    print(f"\n{'='*60}")
    print(f"  跨项目模式分析")
    print(f"{'='*60}")

    for d in all_data:
        print(f"\n  📖 {d['name']}")
        print(f"     状态: {d['status']}  |  章节: {d['chapters']}  |  已完成: {d['completed']}")
        print(f"     平均章字数: {d['avg_chapter_chars']:,}")
        if d["hook_types"]:
            hooks_str = ", ".join(f"{k}:{v}" for k, v in sorted(d["hook_types"].items(), key=lambda x: x[1], reverse=True))
            print(f"     钩子类型: {hooks_str}")

    insights = generate_insights(all_data)

    print(f"\n{'─'*60}")
    print(f"  💡 跨项目洞察")
    print(f"{'─'*60}")
    for i, insight in enumerate(insights, 1):
        print(f"\n  {i}. {insight}")

    print(f"\n  是否将分析结果同步到共享库？")
    ans = input("  (y/N): ").strip().lower()
    if ans == 'y':
        update_library(stories_path, all_data, insights)

    print()


if __name__ == "__main__":
    main()

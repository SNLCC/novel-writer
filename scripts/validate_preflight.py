#!/usr/bin/env python3
"""
validate_preflight.py — 验证章节 PRE-FLIGHT 清单是否已确认

用法:
    python validate_preflight.py <章节号> [--novel <小说目录>]

检查项：
    1. 4 份必读文件是否被标记为已读
    2. 钩子类型是否已确认（非「待定」/ 空）
    3. 前300字冲突是否已确认
    4. 需回收悬念是否被标记

如果检查未通过，打印缺失项并返回非 0 退出码。
"""

import argparse
import re
import sys
from pathlib import Path

from _utils import require_novel_path


def count_real_files(novel_path):
    """统计 4 份必读文件中有多少实际存在"""
    files = [
        novel_path / "story-bible.md",
        novel_path / "outline",
        novel_path / "notes" / "suspense-tracking.md",
        novel_path / "characters",
    ]
    count = 0
    if files[0].exists():
        count += 1
    if files[1].exists() and list(files[1].glob("arc-*.md")):
        count += 1
    if files[2].exists():
        count += 1
    if files[3].exists() and list(files[3].glob("*.md")):
        count += 1
    return count


def validate(chapter_file, novel_path):
    """验证章节的 PRE-FLIGHT 清单"""
    if not chapter_file.exists():
        return False, [f"章节文件不存在: {chapter_file}"]

    content = chapter_file.read_text(encoding="utf-8")

    # 找到 PRE-FLIGHT 区域
    preflight_start = content.find("PRE-FLIGHT")
    if preflight_start == -1:
        return False, ["未找到 PRE-FLIGHT 清单"]

    # 提取 PRE-FLIGHT 到「正文」之间的内容
    body_start = content.find("## 正文", preflight_start)
    if body_start == -1:
        body_start = len(content)
    preflight_section = content[preflight_start:body_start]

    issues = []

    # 检查 1：4 份文件是否被标记已读
    required_reads = [
        ("story-bible.md", ["story-bible"]),
        ("outline", ["outline/arc", "outline"]),
        ("suspense-tracking.md", ["suspense-tracking"]),
        ("characters/人物档案", ["characters/", "人物档案", "出场人物"]),
    ]
    for label, keywords in required_reads:
        found = False
        for line in preflight_section.split("\n"):
            if any(kw in line for kw in keywords):
                if "[x]" in line.lower():
                    found = True
                    break
                if "[ ]" in line:
                    issues.append(f"未读: {label}（清单未勾选）")
                    found = True
                    break
        if not found:
            issues.append(f"缺少: {label} 的检查项")

    # 检查 1b：场景档案是否被标记已读
    has_scene_check = False
    for line in preflight_section.split("\n"):
        if "scenes/" in line:
            if "[x]" in line.lower():
                has_scene_check = True
                break
            if "[ ]" in line:
                issues.append("场景描写锚点: 清单未勾选")
                has_scene_check = True
                break
    # 如果章节没有场景检查项，不算错误（可能本章无已知场景）

    # 检查 2：钩子类型是否已确认
    hook_line = ""
    for line in preflight_section.split("\n"):
        if "钩子类型确认" in line or "钩子类型" in line:
            hook_line = line
            break

    if hook_line:
        if "[x]" in hook_line.lower():
            pass  # 已勾选确认
        elif "**" in hook_line:
            hook_val = hook_line.split("**")[-1].strip()
            # 如果 split 结果是空（因为 ** 在末尾），也认为未确认
            if not hook_val or hook_val in ("待定", "...", "…", "（结尾）：[具体钩子内容]", "[具体钩子内容]"):
                issues.append("钩子类型未确认（仍为占位符）")
        elif "[ ]" in hook_line:
            issues.append("钩子类型: 清单未勾选")
    else:
        issues.append("缺少钩子类型检查项")

    # 检查 3：前300字冲突是否确认
    conflict_confirmed = False
    for line in preflight_section.split("\n"):
        if "前300字冲突" in line:
            if "[x]" in line.lower():
                conflict_confirmed = True
            elif "**" in line:
                val = line.split("**")[-1].strip()
                if val and val not in ("待定", "...", "…", "[开篇即冲突——具体写什么]"):
                    conflict_confirmed = True
            break

    if not conflict_confirmed:
        issues.append("前300字冲突未确认")

    # 检查 4：悬念回收是否被标记
    suspense_lines = [l for l in preflight_section.split("\n") if "需回收悬念" in l]
    unresolved = [l for l in suspense_lines if "[ ]" in l]
    if unresolved:
        issues.append(f"有 {len(unresolved)} 个需回收悬念未确认")

    if issues:
        return False, issues
    return True, []


def main():
    parser = argparse.ArgumentParser(description="验证 PRE-FLIGHT 清单")
    parser.add_argument("chapter", type=int, help="章节号")
    parser.add_argument("--novel", default=None, help="小说项目目录")
    args = parser.parse_args()

    novel_path = require_novel_path(args.novel)

    chapter_file = novel_path / "chapters" / f"ch-{args.chapter:02d}.md"
    ok, issues = validate(chapter_file, novel_path)

    if ok:
        print(f"✅ ch-{args.chapter:02d} PRE-FLIGHT 检查通过，可以开始写作。")
        sys.exit(0)
    else:
        print(f"❌ ch-{args.chapter:02d} PRE-FLIGHT 检查未通过：\n")
        for i in issues:
            print(f"  - {i}")
        print(f"\n请完成上述检查项后再开始写作。")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
check_consistency.py — 设定一致性检查

用法:
    python check_consistency.py [--novel <小说目录>]

如果不指定 --novel，自动读取 .current-novel 或使用当前目录。

检查项：
    1. 故事圣经中声明的人物是否都有档案
    2. 悬念追踪表是否有孤儿悬念（超期未回收）
    3. 章节状态与元信息是否一致
    4. 大纲中的章节数与实际章节是否匹配
"""

import argparse
import re
import sys
from pathlib import Path

from _utils import resolve_novel_path


# ── 角色名过滤器 ────────────────────────────────────────────

_EXACT_BLACKLIST = {
    "...", "N", "待定", "其他", "内容", "字段", "名字",
    "地图", "年代", "类型", "状态", "详情", "具体", "描述",
}

_SUBSTR_BLACKLIST = [
    "势力", "组织", "家族", "门派",
    "绝不能", "禁止",
    "关系图谱", "关系变化",
    "事件描述", "核心冲突", "冲突描述",
    "钩子", "卷名", "章节", "标题",
    "如有", "例如", "一句话",
    "计划回收", "埋设章",
    "恋人", "师徒", "敌对", "朋友", "亲人", "同门", "陌生",
]


def _is_likely_character_name(s):
    s = s.strip()
    if not s or len(s) > 12:
        return False
    if s in _EXACT_BLACKLIST:
        return False
    for kw in _SUBSTR_BLACKLIST:
        if kw in s:
            return False
    if re.match(r'^(盟友|反派|导师|势力|配角|主角|路人|规则)[A-Z]?$', s):
        return False
    if re.match(r'^规则\d*$', s):
        return False
    if s.startswith("[") or s.endswith("]"):
        return False
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', s))
    has_alpha = bool(re.search(r'[A-Za-z]{2,}', s))
    return has_chinese or has_alpha



def check_characters_in_bible(novel_path):
    issues = []
    bible_file = novel_path / "story-bible.md"
    if not bible_file.exists():
        return ["story-bible.md 不存在"]

    bible_text = bible_file.read_text(encoding="utf-8")
    char_pattern = re.findall(r'\[([^\]]+)\]', bible_text)
    known_chars = set()
    for c in char_pattern:
        if _is_likely_character_name(c):
            known_chars.add(c.strip())

    chars_dir = novel_path / "characters"
    existing = set()
    if chars_dir.exists():
        for f in chars_dir.glob("*.md"):
            existing.add(f.stem)

    issues = []
    for c in sorted(known_chars):
        if c not in existing:
            issues.append(f"story-bible.md 提到「{c}」但 characters/{c}.md 不存在")
    return issues


def check_suspense_orphans(novel_path):
    issues = []
    suspense_file = novel_path / "notes" / "suspense-tracking.md"
    if not suspense_file.exists():
        return issues

    content = suspense_file.read_text(encoding="utf-8")
    header_kw = {"编号", "悬念内容", "埋设章", "计划回收章", "状态"}

    for line in content.split("\n"):
        if any(kw in line for kw in header_kw):
            continue
        if "---" in line or not line.strip():
            continue
        if "未回收" not in line and "|" not in line:
            continue
        if "|" not in line:
            continue

        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 3:
            continue

        sid, scontent = parts[0], parts[1]
        if scontent.startswith("[") and scontent.endswith("]"):
            continue

        plan_ch = parts[3] if len(parts) > 3 else "?"
        actual_ch = parts[4] if len(parts) > 4 else "-"

        if re.search(r'\d+', plan_ch):
            issues.append(
                f"未回收悬念 {sid}：{scontent} "
                f"（计划 {plan_ch}，实际 {actual_ch}）"
            )
    return issues


def check_chapter_counts(novel_path):
    issues = []
    meta_file = novel_path / "meta.md"
    chapters_dir = novel_path / "chapters"
    if not meta_file.exists():
        return issues

    meta_text = meta_file.read_text(encoding="utf-8")
    m = re.search(r'\*\*当前章节\*\*\s*\|\s*(\d+)', meta_text)
    declared = int(m.group(1)) if m else 0

    if chapters_dir.exists():
        chapter_files = list(chapters_dir.glob("ch-*.md"))
        actual = len(chapter_files)
        if declared != actual:
            issues.append(
                f"meta.md 声明 {declared} 章，但 chapters/ 下有 {actual} 个章节文件"
            )
        nums = []
        for f in chapter_files:
            m2 = re.search(r'ch-(\d+)', f.name)
            if m2:
                nums.append(int(m2.group(1)))
        if nums:
            nums.sort()
            for i in range(len(nums) - 1):
                if nums[i + 1] - nums[i] > 1:
                    issues.append(f"章节编号跳跃：ch-{nums[i]:02d} -> ch-{nums[i+1]:02d}")
    return issues


def check_character_arcs(novel_path):
    """检查人物档案的弧线追踪是否保持更新"""
    issues = []
    chars_dir = novel_path / "characters"
    if not chars_dir.exists():
        return issues

    chapters_dir = novel_path / "chapters"
    if not chapters_dir.exists():
        return issues

    # 找到最新的章节号
    chapter_nums = []
    for f in chapters_dir.glob("ch-*.md"):
        m = re.search(r'ch-(\d+)', f.name)
        if m:
            chapter_nums.append(int(m.group(1)))
    if not chapter_nums:
        return issues
    latest_ch = max(chapter_nums)

    for char_file in sorted(chars_dir.glob("*.md")):
        text = char_file.read_text(encoding="utf-8")
        # 提取「出场记录」表中的最后一行章节号
        in_appearance_table = False
        last_chapter_mentioned = 0
        for line in text.split("\n"):
            if "出场记录" in line:
                in_appearance_table = True
                continue
            if in_appearance_table:
                if line.startswith("##") or line.startswith("---"):
                    break
                m = re.match(r'\|\s*ch-(\d+)\s*\|', line)
                if m:
                    last_chapter_mentioned = max(last_chapter_mentioned, int(m.group(1)))

        if last_chapter_mentioned > 0 and last_chapter_mentioned < latest_ch - 10:
            issues.append(
                f"{char_file.stem} 的出场记录停在 ch-{last_chapter_mentioned:02d}，"
                f"但最新章已是 ch-{latest_ch:02d}（落后 {latest_ch - last_chapter_mentioned} 章）"
            )

    return issues


def check_outline_completion(novel_path):
    issues = []
    outline_dir = novel_path / "outline"
    chapters_dir = novel_path / "chapters"
    if not outline_dir.exists():
        return issues

    existing_chapters = set()
    if chapters_dir.exists():
        for f in chapters_dir.glob("ch-*.md"):
            m = re.search(r'ch-(\d+)', f.name)
            if m:
                existing_chapters.add(int(m.group(1)))

    header_kw = {"章节", "钩子", "核心", "---", "状态"}

    for arc_file in sorted(outline_dir.glob("arc-*.md")):
        content = arc_file.read_text(encoding="utf-8")
        planned = set()
        for line in content.split("\n"):
            if any(kw in line for kw in header_kw):
                continue
            m = re.match(r'\|\s*(\d+)\s*\|', line)
            if m:
                if re.search(r'\[\S+\]', line):
                    continue
                planned.add(int(m.group(1)))

        missing = planned - existing_chapters
        if missing and len(planned) > 0:
            missing_sorted = sorted(missing)[:5]
            suffix = "..." if len(missing) > 5 else ""
            issues.append(
                f"{arc_file.name} 规划了章节但未创建文件: "
                f"{', '.join(f'ch-{n:02d}' for n in missing_sorted)}{suffix}"
            )
    return issues


# ── 主入口 ──────────────────────────────────────────────────
def check_scene_drift(novel_path):
    """检查场景档案是否与章节一致"""
    issues = []
    scenes_dir = novel_path / "scenes"
    if not scenes_dir.exists() or not list(scenes_dir.glob("*.md")):
        return issues

    chapters_dir = novel_path / "chapters"
    chapter_files = sorted(chapters_dir.glob("ch-*.md")) if chapters_dir.exists() else []

    scene_files = [f for f in scenes_dir.glob("*.md") if not f.name.startswith(".")]

    # 检查每个场景档案是否有出场记录
    for sf in scene_files:
        text = sf.read_text(encoding="utf-8")
        # Count appearance records
        appearances = len(re.findall(r"\|\s*ch-\d+", text))
        if appearances == 0:
            issues.append(f"场景「{sf.stem}」无出场记录，可能未在章节中使用或漏记")
        elif chapter_files and appearances < len(chapter_files) * 0.05:
            # Very low appearance rate - might be stale
            pass

    return issues


def check_clue_tracking(novel_path):
    """检查线索追踪表完整性"""
    issues = []
    tf = novel_path / "notes" / "suspense-tracking.md"
    if not tf.exists():
        return issues

    content = tf.read_text(encoding="utf-8")
    header_kw = {"编号", "类型", "内容", "埋设章", "计划揭示章", "状态"}

    entries = []
    for line in content.split("\n"):
        if any(kw in line for kw in header_kw):
            continue
        if "---" in line or not line.strip():
            continue
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 7:
            continue
        # Skip placeholders
        if parts[1] in ("[类型]", "类型"):
            continue
        content_val = parts[2] if len(parts) > 2 else ""
        if content_val.startswith("[") and content_val.endswith("]"):
            continue

        status = parts[6] if len(parts) > 6 else "?"
        planned = parts[4] if len(parts) > 4 else "?"
        entry_type = parts[1] if len(parts) > 1 else "?"

        if "未回收" in status:
            m = re.search(r"(\d+)", planned)
            if m:
                planned_ch = int(m.group(1))
                chapters_dir = novel_path / "chapters"
                max_ch = len(list(chapters_dir.glob("ch-*.md"))) if chapters_dir.exists() else 0
                if max_ch > 0 and max_ch - planned_ch > 10:
                    issues.append(
                        f"孤儿{entry_type} S{planned_ch}: {content_val[:30]} "
                        f"（超期 {max_ch - planned_ch} 章）"
                    )
                elif max_ch > 0 and max_ch - planned_ch > 5:
                    issues.append(
                        f"即将过期{entry_type} S{planned_ch}: {content_val[:30]} "
                        f"（超期 {max_ch - planned_ch} 章）"
                    )

    return issues


def main():
    parser = argparse.ArgumentParser(description="设定一致性检查")
    parser.add_argument("--novel", default=None, help="小说项目目录（默认自动检测）")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)
    if not (novel_path / "story-bible.md").exists():
        print("[ERROR] 未找到 story-bible.md，请确认目录正确")
        print(f"  当前路径: {novel_path}")
        sys.exit(1)

    print(f"一致性检查: {novel_path.name}\n")
    all_issues = []

    checks = [
        ("人物档案完整性", check_characters_in_bible),
        ("悬念追踪", check_suspense_orphans),
        ("章节计数一致", check_chapter_counts),
        ("大纲-实际匹配", check_outline_completion),
        ("人物弧线更新", check_character_arcs),
    ]

    for i, (label, fn) in enumerate(checks, 1):
        print("-" * 50)
        print(f"检查 {i}：{label}")
        issues = fn(novel_path)
        all_issues.extend(issues)
        if issues:
            for item in issues:
                print(f"  ! {item}")
        else:
            print("  OK 通过")

    print("-" * 50)
    if all_issues:
        print(f"\n发现 {len(all_issues)} 个问题，请逐一处理。")
    else:
        print(f"\n所有检查通过！")


if __name__ == "__main__":
    main()

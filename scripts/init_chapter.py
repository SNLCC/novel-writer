#!/usr/bin/env python3
"""
init_chapter.py — 为新章节生成 PRE-FLIGHT 检查清单和草稿框架

用法:
    python init_chapter.py <章节号> [--novel <小说目录>] [--arc <卷号>]

流程：
    1. 从卷大纲（表格或细纲）提取本章的钩子类型和核心冲突
    2. 从悬念追踪表提取本章需回收的悬念
    3. 生成章节文件（含 PRE-FLIGHT 清单）
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


def find_arc_for_chapter(arc_dir, chapter_num):
    if not arc_dir.exists():
        return None
    ch_ref = f"ch-{chapter_num:02d}"
    for arc_file in sorted(arc_dir.glob("arc-*.md")):
        content = arc_file.read_text(encoding="utf-8")
        if ch_ref in content or f"ch-{chapter_num}" in content:
            return arc_file
    for arc_file in sorted(arc_dir.glob("arc-*.md")):
        content = arc_file.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if re.match(rf'\|\s*{chapter_num}\s*\|', line):
                return arc_file
            if re.match(rf'###\s*第\s*{chapter_num}\s*章', line):
                return arc_file
    return None


def parse_table_row(line):
    line = line.strip().strip("|")
    return [c.strip() for c in line.split("|")]


def extract_chapter_info(arc_file, chapter_num):
    info = {
        "title": f"第{chapter_num}章",
        "hook_type": "待定",
        "conflict": "待定",
        "word_count": "待定",
        "arc_num": "XX",
    }
    if not arc_file or not arc_file.exists():
        return info

    m = re.search(r'arc-(\d+)', arc_file.name)
    if m:
        info["arc_num"] = m.group(1)

    content = arc_file.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Method 1: table row (| ch | title | hook | conflict | words | status |)
    for line in lines:
        if re.match(rf'\|\s*{chapter_num}\s*\|', line):
            cells = parse_table_row(line)
            if len(cells) >= 3 and cells[1] and cells[1] not in ("---", "标题"):
                info["title"] = cells[1]
            if len(cells) >= 4 and cells[2] and cells[2] not in ("---", "钩子类型"):
                info["hook_type"] = cells[2]
            if len(cells) >= 5 and cells[3] and cells[3] not in ("---", "核心冲突"):
                info["conflict"] = cells[3]
            if len(cells) >= 6 and cells[4] and cells[4] not in ("---", "字数"):
                info["word_count"] = cells[4]
            break

    # Method 2: ### 第 X 章：Title
    m = re.search(rf'###\s*第\s*{chapter_num}\s*章[：:]\s*(.+)', content)
    if m:
        info["title"] = f"第{chapter_num}章：{m.group(1).strip()}"

    # Method 3: extract from detail section keywords
    section_start = None
    for i, line in enumerate(lines):
        if re.match(rf'###\s*第\s*{chapter_num}\s*章', line):
            section_start = i
            break

    if section_start is not None:
        for j in range(section_start, min(section_start + 30, len(lines))):
            line = lines[j]
            if j > section_start and re.match(r'###\s*第\s*\d+\s*章', line):
                break
            if "钩子设计" in line:
                val = line.split("**")[-1].strip("：: ").strip()
                if val and val not in ("...", "…"):
                    info["hook_type"] = val[:30]
            if "前300字冲突" in line or "核心冲突" in line:
                val = line.split("**")[-1].strip("：: ").strip()
                if val and val not in ("...", "…"):
                    info["conflict"] = val[:50]

    return info


def get_pending_suspense(suspense_file, chapter_num):
    pending = []
    if not suspense_file.exists():
        return pending

    content = suspense_file.read_text(encoding="utf-8")
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
        if len(parts) < 4:
            continue

        status = parts[-1] if len(parts) >= 6 else parts[4] if len(parts) >= 5 else ""
        if "已回收" in status:
            continue

        scontent = parts[1]
        if scontent.startswith("[") and scontent.endswith("]"):
            continue

        plan_ch = parts[3]
        try:
            plan_num = int(re.search(r'(\d+)', plan_ch).group(1))
            if plan_num <= chapter_num:
                pending.append({
                    "id": parts[0],
                    "content": scontent,
                    "plan": plan_ch,
                })
        except (AttributeError, ValueError):
            pass

    return pending


def generate_chapter(novel_path, chapter_num, arc_num):
    chapters_dir = novel_path / "chapters"
    chapters_dir.mkdir(exist_ok=True)

    filename = f"ch-{chapter_num:02d}.md"
    chapter_file = chapters_dir / filename

    if chapter_file.exists():
        print(f"[WARN] 章节文件已存在: {chapter_file}")
        response = input("  覆盖？(y/N): ").strip().lower()
        if response != 'y':
            print("  已取消。")
            return

    arc_dir = novel_path / "outline"
    if arc_num:
        arc_file = arc_dir / f"arc-{arc_num:02d}.md"
    else:
        arc_file = find_arc_for_chapter(arc_dir, chapter_num)

    chapter_info = extract_chapter_info(arc_file, chapter_num)
    pending_suspense = get_pending_suspense(
        novel_path / "notes" / "suspense-tracking.md", chapter_num
    )

    # 检测本章可能涉及的场景
    scene_reminders = []
    scenes_dir = novel_path / "scenes"
    if arc_file and arc_file.exists():
        arc_text = arc_file.read_text(encoding="utf-8")
        if scenes_dir.exists():
            for sf in scenes_dir.glob("*.md"):
                if sf.stem in arc_text and not sf.name.startswith("."):
                    scene_reminders.append(sf.stem)
    
    # 发现本章可能涉及的人物
    character_reminders = []
    chars_dir = novel_path / "characters"
    known_chars = []
    if chars_dir.exists():
        known_chars = [f.stem for f in chars_dir.glob("*.md")]
    # 在大纲中搜索提及的人物名
    if arc_file and arc_file.exists():
        arc_text = arc_file.read_text(encoding="utf-8")
        for name in known_chars:
            if name in arc_text:
                character_reminders.append(name)

    today = datetime.now().strftime("%Y-%m-%d")

    if character_reminders:
        char_lines = "\n".join(
            f"- [ ] 检查人物弧线：characters/{name}.md"
            for name in sorted(character_reminders)[:8]
        )
        if len(character_reminders) > 8:
            char_lines += f"\n- [ ] ...及其他 {len(character_reminders) - 8} 人"
    else:
        char_lines = "- [ ] 确认本章出场人物，检查对应人物档案"

    if pending_suspense:
        suspense_lines = "\n".join(
            f"- [ ] 需回收悬念 {s['id']}：{s['content']}（计划 {s['plan']}）"
            for s in pending_suspense
        )
    else:
        suspense_lines = "- [ ] 本章无需回收的悬念"

    arc_tag = str(arc_num) if arc_num else chapter_info["arc_num"]

    content = f"""# {chapter_info['title']}

> **状态**：草稿
> **字数**：{chapter_info['word_count']}
> **日期**：{today}

---

## PRE-FLIGHT 检查清单（写前必读）

- [ ] 已读 story-bible.md（世界观/规则无冲突）
- [ ] 已读 outline/arc-{arc_tag}.md 本章大纲
- [ ] 已读 notes/suspense-tracking.md（确认需回收/新埋的悬念）
{char_lines}
- [ ] 钩子类型确认：**{chapter_info['hook_type']}**
- [ ] 前300字冲突确认：**{chapter_info['conflict']}**
{suspense_lines}

---

## 正文

[在此写作]

---

## 写后归档

### 本章摘要
[3-5句话概括本章核心内容]

### 新设定
- [如有新增设定，运行 python scripts/append_bible.py --section <分区> --content "<设定>" 追加到 story-bible.md（自动去重）]

### 人物变化
- [行为 / 关系 / 状态的改变，必须同步到对应人物档案]

### 悬念追踪
- 回收：[本章回收了哪些悬念]
- 新埋：[本章埋了哪些新悬念]

### 钩子执行
- [结尾钩子是否到位 / 读者预期反应]
"""

    chapter_file.write_text(content, encoding="utf-8")
    print(f"[OK] 创建章节文件: {chapter_file}")
    print(f"  标题: {chapter_info['title']}")
    print(f"  钩子类型: {chapter_info['hook_type']}")
    print(f"  核心冲突: {chapter_info['conflict']}")
    print(f"  对应卷: arc-{arc_tag}")
    if pending_suspense:
        print(f"  需回收悬念: {len(pending_suspense)} 个")
    print(f"\nPRE-FLIGHT 检查清单已嵌入章节文件。开始写作前请逐项确认。")


def main():
    parser = argparse.ArgumentParser(description="初始化新章节")
    parser.add_argument("chapter", type=int, help="章节号")
    parser.add_argument("--novel", default=None, help="小说项目目录（默认自动检测）")
    parser.add_argument("--arc", type=int, default=None, help="卷号（自动检测）")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)

    if not novel_path.exists():
        print(f"[ERROR] 目录不存在: {novel_path}")
        sys.exit(1)

    if not (novel_path / "story-bible.md").exists():
        print(f"[WARN] 未找到 story-bible.md，这可能不是小说项目目录")

    generate_chapter(novel_path, args.chapter, args.arc)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
append_bible.py — 向故事圣经安全追加新设定（含自动去重）

用法:
    python append_bible.py --section <分区> --content "<设定内容>" [--novel <小说目录>]
    python append_bible.py --section <分区> --file <临时文件路径>

分区（section）:
    世界观-背景    →  §1.1 时代背景
    世界观-地理    →  §1.2 地理与势力
    世界观-力量    →  §1.3 力量体系 / 规则
    世界观-社会    →  §1.4 社会结构
    核心规则       →  §二、核心规则
    势力关系       →  §三、家族 / 势力关系
    节奏法则       →  §四、节奏法则
    禁忌           →  §五、禁忌清单

功能：
    - 自动定位到指定分区
    - 模糊去重：与已有内容比较相似度，≥70% 则提示跳过
    - 支持交互确认（默认）或 --force 强制追加
    - 追加后在文件末尾添加变更日志
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime

from _utils import resolve_novel_path


# ── 分区映射 ────────────────────────────────────────────────

def tokenize(text):
    """简单分词：按中文单字切分，过滤标点"""
    text = re.sub(r'[，。、；：""''！？…—\s\n\r]', '', text)
    return set(text)


def similarity(a, b):
    """Jaccard 相似度"""
    set_a = tokenize(a)
    set_b = tokenize(b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def find_similar(content, section_text, threshold=0.65):
    """在分区文本中查找相似内容。返回 (similar_line, score) 或 None"""
    # 将分区文本拆成有意义的块（按行或段落）
    lines = [l.strip() for l in section_text.split("\n") if l.strip() and not l.strip().startswith("#")]
    # 按句子拆分
    blocks = []
    for line in lines:
        # 拆除非表格、非列表标记的行
        if line.startswith("|") or line.startswith("-"):
            blocks.append(line)
        else:
            sentences = re.split(r'[。；]', line)
            blocks.extend(s for s in sentences if len(s) > 4)

    best_score = 0.0
    best_block = ""
    for block in blocks:
        score = similarity(content, block)
        if score > best_score:
            best_score = score
            best_block = block

    if best_score >= threshold:
        return best_block[:80], best_score
    return None


# ── 核心逻辑 ─────────────────────────────────────────────────

def append_to_bible(novel_path, section_key, content, force=False):
    bible_file = novel_path / "story-bible.md"

    if not bible_file.exists():
        print(f"[ERROR] story-bible.md 不存在: {bible_file}")
        sys.exit(1)

    if section_key not in SECTION_MAP:
        print(f"[ERROR] 未知分区: {section_key}")
        print(f"  可用分区: {', '.join(SECTION_MAP.keys())}")
        sys.exit(1)

    section_header, next_section = SECTION_MAP[section_key]
    bible_text = bible_file.read_text(encoding="utf-8")
    lines = bible_text.split("\n")

    # 定位分区范围
    start_idx = None
    end_idx = len(lines)

    for i, line in enumerate(lines):
        if section_header in line:
            start_idx = i
            break

    if start_idx is None:
        print(f"[ERROR] 未找到分区「{section_header}」")
        print("  请确认 story-bible.md 结构完整。")
        sys.exit(1)

    if next_section:
        for j in range(start_idx + 1, len(lines)):
            if next_section in lines[j]:
                end_idx = j
                break

    section_lines = lines[start_idx:end_idx]
    section_text = "\n".join(section_lines)

    # 去重检查
    similar = find_similar(content, section_text)
    if similar:
        sim_text, sim_score = similar
        print(f"\n⚠️  疑似重复设定（相似度 {sim_score:.0%}）：")
        print(f"  已有: {sim_text}")
        print(f"  新增: {content[:80]}")
        if not force:
            ans = input("\n  是否仍要追加？(y/N): ").strip().lower()
            if ans != 'y':
                print("  已跳过。")
                return False
        else:
            print("  --force 已指定，强制追加。")

    # 在分区末尾追加
    insert_idx = end_idx

    # 确定追加格式
    if "核心规则" in section_key or "禁忌" in section_key:
        # 编号列表
        existing_numbers = []
        for line in section_lines:
            m = re.match(r'(\d+)\.', line.strip())
            if m:
                existing_numbers.append(int(m.group(1)))
        next_num = max(existing_numbers) + 1 if existing_numbers else 1
        new_line = f"{next_num}. {content}"
    elif "势力关系" in section_key:
        new_line = f"- {content}"
    elif "节奏法则" in section_key:
        new_line = f"- {content}"
    else:
        new_line = f"- {content}"

    # 确保前面有空行
    if insert_idx > 0 and lines[insert_idx - 1].strip():
        lines.insert(insert_idx, "")
        insert_idx += 1

    lines.insert(insert_idx, new_line)
    insert_idx += 1

    # 添加变更日志
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_entry = (
        f"\n<!-- CHANGELOG: [{today}] [{section_key}] {content[:60]} -->"
    )
    lines.append(log_entry)

    bible_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✅ 已追加到「{section_header}」：")
    print(f"   {new_line}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="向故事圣经安全追加新设定（含自动去重）"
    )
    parser.add_argument("--section", required=True,
                        help=f"目标分区: {', '.join(SECTION_MAP.keys())}")
    parser.add_argument("--content", default=None, help="设定内容（直接传入）")
    parser.add_argument("--file", default=None, help="从文件读取设定内容")
    parser.add_argument("--novel", default=None, help="小说项目目录")
    parser.add_argument("--force", action="store_true", help="跳过去重确认，强制追加")
    args = parser.parse_args()

    # 获取内容
    if args.content:
        content = args.content
    elif args.file:
        fp = Path(args.file)
        if not fp.exists():
            print(f"[ERROR] 文件不存在: {fp}")
            sys.exit(1)
        content = fp.read_text(encoding="utf-8").strip()
    else:
        # 交互输入
        print("请输入新设定内容（输入空行结束）：")
        lines_input = []
        while True:
            line = input()
            if not line:
                break
            lines_input.append(line)
        content = "\n".join(lines_input)

    if not content:
        print("[ERROR] 内容为空。")
        sys.exit(1)

    novel_path = resolve_novel_path(args.novel)
    append_to_bible(novel_path, args.section, content, args.force)


if __name__ == "__main__":
    main()

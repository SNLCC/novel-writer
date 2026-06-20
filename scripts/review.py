#!/usr/bin/env python3
"""
review.py — 结构化复盘引导

用法:
    python review.py [--novel <小说目录>] [--type volume|novel|chapter]
    python review.py --novel <目录> --type volume --volume 1
    python review.py --novel <目录> --type novel

复盘类型：
    volume  — 卷复盘（每卷结束后）
    novel   — 全书复盘（完结后）
    chapter — 章节批量复盘（每10章）

复盘维度：
    1. 节奏与爽点
    2. 人物弧线推进
    3. 悬念/线索/伏笔管理
    4. 读者留存评估
    5. 写作效率与流程
    6. 经验提炼（追加到共享库）
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


REVIEW_PROMPTS = {
    "volume": [
        {
            "dimension": "节奏与爽点",
            "questions": [
                "本卷的爽点密度是否合理？哪里太密集/太稀疏？（对照 story-bible.md 的节奏设定）",
                "情绪曲线是否有连续3章以上走平或下降的情况？",
                "每章结尾钩子是否到位？有没有虚假钩子（下章没接）？",
                "本卷的小爽点和大爽点分别分布在哪几章？节奏是否符合预期？",
            ],
        },
        {
            "dimension": "人物弧线推进",
            "questions": [
                "主角在本卷中有没有可感知的成长/变化？",
                "配角的发展是否偏离了弧线规划？",
                "有没有人物在本卷中「消失」了？（出场后长期未出现）",
                "读者对主角的情感绑定是否加深了？（初见→共鸣→成长→牺牲）",
            ],
        },
        {
            "dimension": "悬念/线索/伏笔",
            "questions": [
                "本卷埋了多少新悬念/线索/伏笔？回收了多少？",
                "有没有悬念超期未回收（超过计划章10章）？",
                "线索链是否完整？有没有断掉的线索？",
                "伏笔的回收是否让读者有「原来如此」的感觉？",
            ],
        },
        {
            "dimension": "读者留存评估",
            "questions": [
                "如果我是读者，读完本卷最想吐槽什么？",
                "本卷的哪个章节最可能造成读者流失？为什么？",
                "有没有「水字数」的章节？哪些可以压缩或删除？",
                "本卷的「必须知道的下一章」时刻有哪些？",
            ],
        },
        {
            "dimension": "经验提炼",
            "questions": [
                "本卷最成功的设计是什么？（可复用到下卷/下部小说）",
                "本卷最大的教训是什么？（下次如何避免）",
                "有没有新的写作技巧在本卷中被验证有效？",
                "如果要给下卷一个最重要的建议，是什么？",
            ],
        },
    ],
    "novel": [
        {
            "dimension": "整体结构",
            "questions": [
                "全书的4卷结构是否平衡？哪卷最弱？",
                "5个核心事件（激励/转折/中点/至暗/高潮）是否都到位？",
                "主线是否清晰？支线是否喧宾夺主？",
                "结局是否让人满意？有没有烂尾/拖结局？",
            ],
        },
        {
            "dimension": "人物评价",
            "questions": [
                "主角的弧线是否完整？读者会为TA的成长感动吗？",
                "哪个配角最出彩？为什么？能复用到下部作品吗？",
                "反派是否有足够的深度和动机？",
                "有没有人物是多余的？可以合并或删除？",
            ],
        },
        {
            "dimension": "写作数据",
            "questions": [
                "全书总字数？平均每章字数？与计划偏差多少？",
                "写作周期多长？平均每天写多少字？",
                "哪个阶段写作效率最高/最低？为什么？",
                "修订量有多大？哪些章节改得最多？",
            ],
        },
        {
            "dimension": "平台表现（如有发布）",
            "questions": [
                "读者反馈如何？最受欢迎的是哪部分？",
                "追读率/完读率如何？在哪个章节流失最多？",
                "与竞品相比，本书的差异化优势是否体现出来了？",
                "如果重写一次，前3章会怎么改？",
            ],
        },
        {
            "dimension": "经验沉淀",
            "questions": [
                "这本书最大的收获是什么？",
                "有哪些模式/技巧可以沉淀到共享库？",
                "下一本书最想尝试什么不同的做法？",
                "用一句话总结这本书的创作心得。",
            ],
        },
    ],
    "chapter": [
        {
            "dimension": "批量质量",
            "questions": [
                "这10章的整体质量如何？有没有明显的低谷章节？",
                "retention_check 平均分是多少？最低分是哪章？",
                "有没有连续多章使用同一种钩子类型？（需要多样化）",
                "信息密度是否均衡？有没有注水章节？",
            ],
        },
        {
            "dimension": "改进计划",
            "questions": [
                "下10章最需要改进的一个方面是什么？",
                "有没有需要回修的章节？（设定冲突/人物漂移）",
                "接下来的节奏计划是否需要调整？",
            ],
        },
    ],
}


def extract_stats(novel_path):
    """提取当前小说的统计数据"""
    chapters_dir = novel_path / "chapters"
    stats = {"total_chapters": 0, "completed": 0}

    if chapters_dir.exists():
        chapter_files = sorted(chapters_dir.glob("ch-*.md"))
        stats["total_chapters"] = len(chapter_files)
        for cf in chapter_files:
            text = cf.read_text(encoding="utf-8")
            if "已完成" in text:
                stats["completed"] += 1

    # Estimate word count
    total_chars = 0
    if chapters_dir.exists():
        for cf in chapters_dir.glob("ch-*.md"):
            text = cf.read_text(encoding="utf-8")
            body_start = text.find("## 正文")
            body_end = text.find("## 写后归档")
            if body_start != -1:
                body = text[body_start:body_end] if body_end != -1 else text[body_start:]
                body = re.sub(r'[\s\n#\-*>|]', '', body)
                total_chars += len(body)
    stats["estimated_chars"] = total_chars

    return stats


def save_to_library(novel_path, findings):
    """追加复盘发现到共享库"""
    stories_root = novel_path.parent
    shared_dir = stories_root / ".shared"
    shared_dir.mkdir(exist_ok=True)
    lib_file = shared_dir / "pattern-library.md"

    if not lib_file.exists():
        print("[INFO] 共享库不存在，跳过保存")
        return

    text = lib_file.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")

    record = f"| {today} | {novel_path.name} | 复盘 | {findings.get('core', '—')[:40]} | {findings.get('detail', '—')[:60]} |"
    text = text.rstrip() + f"\n{record}"

    lib_file.write_text(text, encoding="utf-8")
    print(f"[OK] 发现已保存到共享库: {lib_file}")


def run_review(novel_path, review_type, volume_num=None):
    stats = extract_stats(novel_path)

    print(f"\n{'='*60}")
    print(f"  📋 {novel_path.name} — {'卷' if review_type == 'volume' else '全书' if review_type == 'novel' else '章节批量'}复盘")
    print(f"{'='*60}")

    # Stats summary
    print(f"\n  📊 当前数据：")
    print(f"     总章节: {stats['total_chapters']}  |  已完成: {stats['completed']}")
    print(f"     累计字数（估）: {stats['estimated_chars']:,} 字")

    prompts = REVIEW_PROMPTS.get(review_type, REVIEW_PROMPTS["chapter"])
    findings = {"core": "", "detail": ""}
    all_answers = []

    for section in prompts:
        print(f"\n{'─'*60}")
        print(f"  【{section['dimension']}】")
        print(f"{'─'*60}")

        for i, q in enumerate(section["questions"], 1):
            print(f"\n  {i}. {q}")
            answer = input("  > ").strip()

            if not answer and i == 1 and section["dimension"] == "经验提炼":
                answer = "（跳过）"
            if answer:
                all_answers.append(f"[{section['dimension']}] {q}\n  → {answer}")

    # Summary
    print(f"\n{'='*60}")
    print(f"\n  ✅ 复盘完成！")
    print(f"\n  你的回答：")
    for a in all_answers:
        print(f"    {a[:100]}")

    # Save to library
    print(f"\n  是否将核心发现保存到共享库？")
    save = input("  (y/N): ").strip().lower()
    if save == 'y':
        core = input("  核心发现（一句话）: ").strip()
        detail = input("  详细说明: ").strip()
        findings = {"core": core, "detail": detail}
        save_to_library(novel_path, findings)

    # Save review log to novel project
    review_dir = novel_path / "notes"
    review_dir.mkdir(exist_ok=True)
    review_file = review_dir / "review-log.md"
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    log_entry = f"\n---\n\n## {today} — {'卷' if review_type == 'volume' else '全书'}复盘\n\n"
    for a in all_answers:
        log_entry += f"- {a}\n"

    existing = ""
    if review_file.exists():
        existing = review_file.read_text(encoding="utf-8")
    review_file.write_text(existing + log_entry, encoding="utf-8")
    print(f"[OK] 复盘记录已保存: {review_file}")

    print()


def main():
    parser = argparse.ArgumentParser(description="结构化复盘引导")
    parser.add_argument("--novel", default=None, help="小说项目目录")
    parser.add_argument("--type", default="volume",
                        choices=["volume", "novel", "chapter"],
                        help="复盘类型")
    parser.add_argument("--volume", type=int, default=None, help="卷号（volume 类型时使用）")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)
    if not novel_path:
        print("[ERROR] 无法定位小说项目。")
        sys.exit(1)

    run_review(novel_path, args.type, args.volume)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
retention_check.py — 章节留存质量自检

用法:
    python retention_check.py <章节号> [--novel <小说目录>] [--platform <平台>]

自检维度（基于网文读者留存数据）：
    1. 前300字冲突检测
    2. 前1000字情绪高点
    3. 主角行动比（做 vs 想）
    4. 结尾钩子质量
    5. 读者好奇心缺口
    6. 主角目标清晰度
    7. 信息密度评估
    8. "有事件发生"检测

输出：每项得分 + 改进建议。不强制通过，供作者参考。
"""

import argparse
import re
import sys
from pathlib import Path


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


# ── 文本提取 ────────────────────────────────────────────────

def extract_body(chapter_file):
    """提取章节正文（PRE-FLIGHT 之后、写后归档之前）"""
    if not chapter_file.exists():
        return None
    text = chapter_file.read_text(encoding="utf-8")
    body_start = text.find("## 正文")
    body_end = text.find("## 写后归档")
    if body_start == -1:
        return None
    if body_end == -1:
        body_end = len(text)
    body = text[body_start:body_end]
    # 去掉标题行
    body = re.sub(r'^## 正文\s*\n*', '', body)
    return body.strip()


def extract_first_n_chars(body, n):
    """提取前N个有效字符（跳过空白和标点）"""
    cleaned = re.sub(r'[\s\n\r#\-*>\|]', '', body)
    return cleaned[:n]


# ── 检查函数 ────────────────────────────────────────────────

CONFLICT_KEYWORDS = [
    "冲突", "对抗", "危机", "威胁", "突然", "竟然", "但是", "然而",
    "不料", "没想到", "危险", "追杀", "围攻", "质问", "逼迫",
    "不得不", "必须", "立即", "紧急", "生死", "绝望", "绝境",
]

EMOTION_KEYWORDS = [
    "愤怒", "恐惧", "狂喜", "哭泣", "眼泪", "颤抖", "激动",
    "震惊", "震撼", "心碎", "绝望", "希望", "温暖", "感动",
    "怒", "喜", "悲", "惊", "怕", "恨", "爱",
]

ACTION_VERBS = [
    "冲", "跑", "跳", "打", "杀", "斩", "刺", "劈", "踢",
    "推", "拉", "抓", "夺", "抢", "逃", "追", "飞", "跃",
    "挥", "砸", "轰", "挡", "拦", "拖", "拽", "抛", "掷",
    "拔", "抽", "拍", "按", "踩", "蹬", "撞", "摔", "翻",
]

THINKING_VERBS = [
    "想", "觉得", "认为", "思考", "回忆", "想起", "记得",
    "感觉", "意识到", "明白", "知道", "决定", "打算",
    "心想", "暗想", "思忖", "寻思", "琢磨", "考虑",
]


def check_conflict_first300(body):
    """检查前300字是否有冲突"""
    first300 = extract_first_n_chars(body, 300)
    hits = [kw for kw in CONFLICT_KEYWORDS if kw in first300]
    score = min(len(hits) * 20, 100)
    if score >= 60:
        return score, f"✅ 发现 {len(hits)} 个冲突信号：{', '.join(hits[:5])}"
    elif score >= 20:
        return score, f"⚠️ 冲突信号偏少（{len(hits)}个），建议在前300字加入更明确的冲突或悬念"
    else:
        return score, "❌ 前300字无冲突信号！建议：人物遇到迫在眉睫的问题 / 抛出悬念 / 强烈情绪瞬间"


def check_emotion_first1000(body):
    """检查前1000字是否有情绪高点"""
    first1000 = extract_first_n_chars(body, 1000)
    hits = [kw for kw in EMOTION_KEYWORDS if kw in first1000]
    # 同时检查感叹号和问号密度
    exclamations = first1000.count("！") + first1000.count("？")
    emotion_density = (len(hits) + exclamations) / max(len(first1000) / 100, 1)

    if emotion_density >= 2.0:
        return 100, f"✅ 情绪信号充足（情绪词 {len(hits)}，标点 {exclamations}）"
    elif emotion_density >= 1.0:
        return 70, f"⚠️ 情绪信号一般，可加强情感渲染"
    elif hits:
        return 40, f"⚠️ 情绪信号偏少（{len(hits)}个），建议增加情感描写"
    else:
        return 10, "❌ 前1000字无情绪信号，读者可能感到平淡"


def check_action_ratio(body):
    """检查主角行动比"""
    action_count = sum(body.count(v) for v in ACTION_VERBS)
    think_count = sum(body.count(v) for v in THINKING_VERBS)

    if action_count == 0 and think_count == 0:
        return 50, "⚠️ 无法评估（正文可能为空或过短）"

    ratio = action_count / max(think_count, 1)

    if ratio >= 3.0:
        return 95, f"✅ 行动力充足（行动词 {action_count} / 思考词 {think_count} = {ratio:.1f}）"
    elif ratio >= 1.5:
        return 75, f"⚠️ 行动略多于思考（{ratio:.1f}:1），可接受"
    elif ratio >= 0.8:
        return 50, f"⚠️ 行动与思考持平（{ratio:.1f}:1），网文读者偏好行动驱动"
    else:
        return 25, f"❌ 思考多于行动（{ratio:.1f}:1）！主角在想 > 在做，读者容易流失"


def check_end_hook(body):
    """检查结尾钩子质量"""
    # 取最后3段
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    if not paragraphs:
        return 0, "❌ 正文为空"

    last_paras = paragraphs[-3:]
    last_text = "\n".join(last_paras)

    # 检测钩子模式
    hook_patterns = {
        "悬念切割": ["突然", "这时", "就在此时", "猛地", "忽然", "竟然"],
        "信息揭露": ["原来", "真相", "秘密", "发现", "揭示", "DNA", "报告", "检测"],
        "冲突升级": ["按下", "引爆", "开战", "出手", "你敢", "动手"],
        "情感高点": ["眼泪", "哭泣", "十年", "终于", "等待", "忍不住"],
        "反向预期": ["不是", "而是", "竟然是", "居然是", "没想到"],
    }

    best_type = None
    best_score = 0
    for hook_type, keywords in hook_patterns.items():
        score = sum(1 for kw in keywords if kw in last_text)
        if score > best_score:
            best_score = score
            best_type = hook_type

    # 检查是否以对话结尾（网文有效钩子）
    ends_with_dialogue = bool(re.search(r'[」""][\s]*$', last_text.strip()))
    ends_with_ellipsis = last_text.strip().endswith("…") or last_text.strip().endswith("...")

    if best_score >= 2:
        return 90, f"✅ 检测到「{best_type}」钩子（{best_score} 个信号）{' + 对话结尾' if ends_with_dialogue else ''}"
    elif best_score >= 1:
        return 65, f"⚠️ 钩子信号较弱（{best_type}），建议加强结尾冲击力"
    elif ends_with_ellipsis:
        return 50, "⚠️ 以省略号结尾，但缺少实质钩子内容"
    elif ends_with_dialogue:
        return 55, "⚠️ 以对话结尾，可接受但建议增加悬念感"
    else:
        return 20, "❌ 结尾无钩子！读者不会点下一章。建议：悬念切割 / 信息揭露 / 冲突升级 / 情感高点 / 反向预期"


def check_curiosity_gap(body):
    """检查读者好奇心缺口"""
    # 统计问号和悬念信号
    questions = body.count("？")
    mystery_signals = sum(1 for kw in ["秘密", "真相", "为什么", "怎么回事", "意味着",
                                        "难道", "莫非", "到底", "究竟", "隐藏"] if kw in body)

    total_chars = len(body.replace("\n", "").replace(" ", ""))
    if total_chars < 100:
        return 0, "❌ 正文过短，无法评估"

    curiosity_density = (questions + mystery_signals) / max(total_chars / 500, 1)

    if curiosity_density >= 2.5:
        return 90, f"✅ 好奇心驱动充足（问号 {questions}，悬念信号 {mystery_signals}）"
    elif curiosity_density >= 1.5:
        return 70, f"⚠️ 好奇心信号适中"
    elif curiosity_density >= 0.5:
        return 45, f"⚠️ 读者好奇心不足，建议增加悬念或未解之谜"
    else:
        return 20, "❌ 缺少好奇心驱动！读者不知道下一步想知道什么"


def check_info_density(body):
    """检查信息密度"""
    total_chars = len(body.replace("\n", "").replace(" ", ""))
    if total_chars < 100:
        return 50, "⚠️ 正文过短，无法评估"

    # 统计专有名词（大写字母开头的词、中文名、地名）
    proper_nouns = len(re.findall(r'[A-Z][a-z]+|[「][^」]{2,10}[」]', body))

    # 统计对话占比
    dialogue_chars = sum(len(m.group()) for m in re.finditer(r'[「""][^」""]+[」""]', body))
    dialogue_ratio = dialogue_chars / max(total_chars, 1)

    # 统计新信息标记
    new_info_markers = sum(1 for kw in ["发现", "得知", "原来", "竟然", "第一次",
                                         "从未", "新的", "最新"] if kw in body)

    info_score = proper_nouns * 5 + new_info_markers * 10

    if info_score >= 40:
        if dialogue_ratio > 0.5:
            return 80, f"✅ 信息量充足（但对话占比 {dialogue_ratio:.0%}，注意节奏）"
        return 90, f"✅ 信息密度良好（专有名词 {proper_nouns}，新信息 {new_info_markers}）"
    elif info_score >= 20:
        return 65, f"⚠️ 信息密度适中"
    else:
        return 35, f"⚠️ 信息密度偏低（专有名词 {proper_nouns}，新信息 {new_info_markers}），可能水分偏多"


def check_something_happens(body):
    """检查是否有「事件发生」"""
    event_keywords = [
        "战斗", "对决", "交手", "攻击", "防御",
        "突破", "晋级", "升级", "进阶",
        "获得", "得到", "发现", "找到",
        "失去", "死亡", "受伤", "牺牲",
        "见面", "对话", "谈判", "交易",
        "背叛", "揭露", "揭穿", "暴露",
        "逃跑", "追击", "追踪", "救援",
        "到达", "离开", "进入", "出发",
    ]
    hits = [kw for kw in event_keywords if kw in body]
    unique_hits = set(hits)

    if len(unique_hits) >= 5:
        return 95, f"✅ 本章有明确事件：{', '.join(sorted(unique_hits)[:5])}"
    elif len(unique_hits) >= 3:
        return 75, f"⚠️ 有事件但不够丰富：{', '.join(sorted(unique_hits))}"
    elif len(unique_hits) >= 1:
        return 45, f"⚠️ 事件单一：{', '.join(sorted(unique_hits))}"
    else:
        return 10, "❌ 本章可能没有实质事件发生！检查是否全是对话/心理描写"


# ── 平台适配 ────────────────────────────────────────────────

# 用户可在 story-bible.md 中设定目标章字数，此处仅作通用参考
DEFAULT_CHAPTER_RANGE = (2000, 6000)  # 宽松默认值


# ── 主逻辑 ─────────────────────────────────────────────────

def run_checks(body):
    checks = [
        ("前300字冲突", check_conflict_first300),
        ("前1000字情绪", check_emotion_first1000),
        ("主角行动比", check_action_ratio),
        ("结尾钩子质量", check_end_hook),
        ("读者好奇心", check_curiosity_gap),
        ("信息密度", check_info_density),
        ("事件检测", check_something_happens),
    ]

    results = []
    for name, func in checks:
        score, msg = func(body)
        results.append({"name": name, "score": score, "msg": msg})

    return results


def print_results(results, body):
    total_chars = len(body.replace("\n", "").replace(" ", ""))

    print(f"\n{'='*60}")
    print(f"  章节留存质量自检")
    print(f"{'='*60}")
    print(f"  正文字数: {total_chars} 字")

    print(f"\n{'─'*60}")

    total_score = 0
    for r in results:
        bar = "█" * (r["score"] // 10) + "░" * (10 - r["score"] // 10)
        icon = "✅" if r["score"] >= 70 else ("⚠️" if r["score"] >= 40 else "❌")
        print(f"\n  {icon} {r['name']}  [{bar}] {r['score']}分")
        print(f"     {r['msg']}")
        total_score += r["score"]

    avg_score = total_score // len(results)

    print(f"\n{'─'*60}")
    print(f"\n  📊 综合评分: {avg_score}/100")

    if avg_score >= 80:
        print(f"  ✅ 本章质量良好，读者留存概率高")
    elif avg_score >= 60:
        print(f"  ⚠️ 本章质量可接受，存在优化空间")
    elif avg_score >= 40:
        print(f"  ⚠️ 本章质量偏低，建议针对性改进")
    else:
        print(f"  ❌ 本章质量较差，强烈建议修改后再发布")



    # 快速改进建议
    low_items = [r for r in results if r["score"] < 60]
    if low_items:
        print(f"\n  🔧 优先改进项（得分 < 60）：")
        for r in low_items:
            print(f"     • {r['name']}（{r['score']}分）")

    print()


def main():
    parser = argparse.ArgumentParser(description="章节留存质量自检")
    parser.add_argument("chapter", type=int, help="章节号")
    parser.add_argument("--novel", default=None, help="小说项目目录")
    parser.add_argument("--platform", default=None,
                        choices=["免费阅读类平台", "起点", "女性向类平台"], help="目标平台")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)
    if not novel_path:
        print("[ERROR] 无法定位小说项目。")
        sys.exit(1)

    chapter_file = novel_path / "chapters" / f"ch-{args.chapter:02d}.md"
    body = extract_body(chapter_file)

    if body is None:
        print(f"[ERROR] 无法读取章节正文: {chapter_file}")
        print("  请确认章节文件存在且包含「## 正文」区域。")
        sys.exit(1)

    if len(body) < 50:
        print(f"[WARN] 正文字数过少（{len(body)} 字），部分检查可能不准确。")

    results = run_checks(body)
    print_results(results, body)


if __name__ == "__main__":
    main()

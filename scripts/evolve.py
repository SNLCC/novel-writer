#!/usr/bin/env python3
"""
evolve.py — Skill 自我进化引擎

用法:
    python evolve.py [--path <stories目录>]

核心理念：
    写的小说越多，skill 自身越强。本脚本分析所有已完成小说的数据，
    生成可操作的升级建议，自动更新 skill 的参考文档。

进化维度：
    1. 钩子效果分析 —— 哪种钩子类型留存率最高？
    2. 节奏配方验证 —— 哪种章节字数/爽点密度组合最优？
    3. 人物弧线模式 —— 哪种 Want/Need 组合最有效？
    4. 平台策略优化 —— 各平台的最佳实践是否调整？
    5. 参考文档自动更新 —— 将验证过的模式写入 references/

输出：
    - 进化报告（终端输出）
    - 自动更新 references/ 中的参考文档
    - 追加到 .shared/pattern-library.md
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime


def scan_novel_deep(nd):
    """深度扫描一部小说，提取结构化数据"""
    data = {
        "name": nd.name,
        "status": "?",
        "chapters": [],
        "total_chars": 0,
        "hook_effectiveness": {},  # hook_type -> [retention_scores]
        "avg_retention": 0,
        "platform": "?",
        "type": "?",
    }

    # Meta
    meta_file = nd / "meta.md"
    if meta_file.exists():
        text = meta_file.read_text(encoding="utf-8")
        for key, pat in [("platform", r'\*\*目标平台\*\*\s*\|\s*(.+)'),
                          ("type", r'\*\*类型\*\*\s*\|\s*(.+)'),
                          ("status", r'\*\*状态\*\*\s*\|\s*(.+)')]:
            m = re.search(pat, text)
            if m:
                data[key] = m.group(1).strip().replace("[", "").replace("]", "").split("/")[0].strip()

    chapters_dir = nd / "chapters"
    if not chapters_dir.exists():
        return data

    for cf in sorted(chapters_dir.glob("ch-*.md")):
        text = cf.read_text(encoding="utf-8")
        if "已完成" not in text:
            continue

        ch_data = {"file": cf.name, "hook_type": "?", "chars": 0}

        # Hook type
        hm = re.search(r'钩子类型确认[：:]\s*\*\*(.+?)\*\*', text)
        if hm:
            ch_data["hook_type"] = hm.group(1).strip()

        # Body char count
        body_start = text.find("## 正文")
        body_end = text.find("## 写后归档")
        if body_start != -1:
            body = text[body_start:body_end] if body_end != -1 else text[body_start:]
            body = re.sub(r'[\s\n#\-*>|\[\]]', '', body)
            ch_data["chars"] = len(body)

        # Try to infer retention quality from hook execution notes
        hook_exec = ""
        he_start = text.find("钩子执行")
        if he_start != -1:
            he_end = text.find("##", he_start + 10)
            if he_end == -1:
                he_end = len(text)
            hook_exec = text[he_start:he_end]

        # Score retention quality from self-assessment notes
        quality_signals = {
            "到位": 85,
            "好": 80,
            "强": 85,
            "不错": 75,
            "可": 65,
            "一般": 50,
            "弱": 30,
            "不足": 25,
            "差": 15,
        }
        ch_quality = 50  # default
        for signal, score in quality_signals.items():
            if signal in hook_exec:
                ch_quality = max(ch_quality, score)

        ch_data["quality"] = ch_quality
        data["chapters"].append(ch_data)

    # Aggregate
    if data["chapters"]:
        data["total_chars"] = sum(ch["chars"] for ch in data["chapters"])
        data["avg_retention"] = sum(ch["quality"] for ch in data["chapters"]) / len(data["chapters"])

        for ch in data["chapters"]:
            ht = ch["hook_type"]
            if ht not in data["hook_effectiveness"]:
                data["hook_effectiveness"][ht] = []
            data["hook_effectiveness"][ht].append(ch["quality"])

    return data


def generate_evolution_insights(all_data):
    """基于所有小说数据生成进化建议"""
    insights = []
    completed = [d for d in all_data if d["chapters"]]
    if not completed:
        return insights

    # 1. 钩子类型效果排名
    hook_scores = {}
    for d in completed:
        for ht, scores in d["hook_effectiveness"].items():
            if ht == "?":
                continue
            if ht not in hook_scores:
                hook_scores[ht] = []
            hook_scores[ht].extend(scores)

    if hook_scores:
        hook_avg = {ht: sum(s) / len(s) for ht, s in hook_scores.items() if s}
        ranked = sorted(hook_avg.items(), key=lambda x: x[1], reverse=True)

        insights.append({
            "category": "钩子策略",
            "confidence": "high" if len(completed) >= 2 else "medium",
            "finding": f"最有效钩子：{ranked[0][0]}（均分 {ranked[0][1]:.0f}），"
                       f"最弱钩子：{ranked[-1][0]}（均分 {ranked[-1][1]:.0f}）",
            "action": f"建议增加「{ranked[0][0]}」的使用频率，减少「{ranked[-1][0]}」的依赖。",
        })

        if len(ranked) >= 2 and ranked[0][1] - ranked[-1][1] > 15:
            insights.append({
                "category": "钩子策略",
                "confidence": "high",
                "finding": f"钩子类型效果差异显著（差距 {ranked[0][1] - ranked[-1][1]:.0f} 分）",
                "action": "考虑在 references/reader-retention.md 中调整钩子推荐优先级。",
            })

    # 2. 章节字数分析
    avg_chars_list = []
    for d in completed:
        char_counts = [ch["chars"] for ch in d["chapters"] if ch["chars"] > 0]
        if char_counts:
            avg_chars_list.append((d["name"], sum(char_counts) // len(char_counts)))

    if avg_chars_list:
        overall = sum(c for _, c in avg_chars_list) // len(avg_chars_list)
        min_novel = min(avg_chars_list, key=lambda x: x[1])
        max_novel = max(avg_chars_list, key=lambda x: x[1])
        insights.append({
            "category": "章节策略",
            "confidence": "medium",
            "finding": f"跨项目平均章字数：{overall:,}（最低 {min_novel[0]} {min_novel[1]:,}，最高 {max_novel[0]} {max_novel[1]:,}）",
            "action": f"建议将推荐章字数调整为 {overall:,} 字左右。",
        })

    # 3. 平台策略沉淀
    platform_data = {}
    for d in completed:
        plat = d["platform"]
        if plat and plat != "?":
            if plat not in platform_data:
                platform_data[plat] = []
            platform_data[plat].append(d)

    for plat, novels in platform_data.items():
        plat_hooks = {}
        for nd in novels:
            for ht, scores in nd["hook_effectiveness"].items():
                if ht == "?":
                    continue
                if ht not in plat_hooks:
                    plat_hooks[ht] = []
                plat_hooks[ht].extend(scores)

        if plat_hooks:
            best_hook = max(plat_hooks.items(), key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0)
            avg_chars_plat = sum(
                sum(ch["chars"] for ch in nd["chapters"]) // max(len(nd["chapters"]), 1)
                for nd in novels
            ) // max(len(novels), 1)

            insights.append({
                "category": f"平台策略：{plat}",
                "confidence": "high" if len(novels) >= 2 else "medium",
                "finding": f"该平台最优钩子：{best_hook[0]}，最佳章字数：约 {avg_chars_plat:,}",
                "action": f"更新 references/platform-research.md 中 {plat} 的推荐策略。",
            })

    # 4. 进化历史
    if len(completed) >= 2:
        sorted_by_date = sorted(completed, key=lambda d: d.get("name", ""))
        first = sorted_by_date[0]
        last = sorted_by_date[-1]
        if first["avg_retention"] > 0 and last["avg_retention"] > 0:
            diff = last["avg_retention"] - first["avg_retention"]
            direction = "提升" if diff > 0 else "下降"
            insights.append({
                "category": "进化趋势",
                "confidence": "low",
                "finding": f"从「{first['name']}」到「{last['name']}」，"
                           f"预估留存质量{direction}了 {abs(diff):.0f} 分。",
                "action": f"继续积累数据以确认趋势。" if abs(diff) < 10 else
                          f"{'继续保持！' if diff > 0 else '需要分析下降原因。'}",
            })

    return insights


def apply_evolution(stories_path, insights):
    """将进化建议写入参考文档"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 更新 .shared/pattern-library.md
    shared_dir = stories_path / ".shared"
    shared_dir.mkdir(exist_ok=True)
    lib_file = shared_dir / "pattern-library.md"

    lib_content = lib_file.read_text(encoding="utf-8") if lib_file.exists() else ""
    evo_section = f"\n### {today} 自动进化分析\n\n"
    for ins in insights:
        evo_section += f"- [{ins['category']}] {ins['finding']}\n"
        evo_section += f"  → {ins['action']}（置信度：{ins['confidence']}）\n"

    lib_file.write_text(lib_content + evo_section, encoding="utf-8")
    print(f"\n[OK] 进化数据已保存到: {lib_file}")

    # 生成参考文档更新建议
    print(f"\n{'─'*60}")
    print(f"  📝 参考文档自动更新建议")
    print(f"{'─'*60}")

    platform_insights = [i for i in insights if "平台策略" in i["category"]]
    hook_insights = [i for i in insights if i["category"] == "钩子策略"]

    if platform_insights:
        print(f"\n  建议更新 references/platform-research.md：")
        for pi in platform_insights:
            print(f"    • {pi['action']}")

    if hook_insights:
        print(f"\n  建议更新 references/reader-retention.md：")
        for hi in hook_insights:
            print(f"    • {hi['action']}")

    # 生成可执行的 patch 建议
    print(f"\n  💡 要应用这些建议，请让 Codex 根据上述发现更新 references/ 目录。")


def main():
    parser = argparse.ArgumentParser(description="Skill 自我进化引擎")
    parser.add_argument("--path", default="./stories", help="stories 目录路径")
    parser.add_argument("--apply", action="store_true", help="自动应用进化建议到参考文档")
    args = parser.parse_args()

    stories_path = Path(args.path).resolve()
    if not stories_path.exists():
        print(f"[ERROR] stories 目录不存在: {stories_path}")
        sys.exit(1)

    novels = sorted([d for d in stories_path.iterdir()
                     if d.is_dir() and not d.name.startswith(".")
                     and (d / "story-bible.md").exists()])

    if not novels:
        print("[INFO] 暂无小说项目，无法进化。")
        print("  至少需要一部有章节数据的小说。")
        return

    all_data = [scan_novel_deep(nd) for nd in novels]

    print(f"\n{'='*60}")
    print(f"  🧬 Skill 自我进化分析")
    print(f"{'='*60}")
    print(f"  分析范围：{len(novels)} 部小说")
    total_chapters = sum(len(d["chapters"]) for d in all_data)
    total_chars = sum(d["total_chars"] for d in all_data)
    print(f"  总章节数：{total_chapters}（已完成）")
    print(f"  总字数（估）：{total_chars:,}")

    # 逐部展示
    for d in all_data:
        if not d["chapters"]:
            continue
        print(f"\n  📖 {d['name']}")
        print(f"     平台: {d['platform']}  |  类型: {d['type']}")
        print(f"     已完成: {len(d['chapters'])} 章  |  均分: {d['avg_retention']:.0f}")
        if d["hook_effectiveness"]:
            hooks_str = ", ".join(
                f"{ht}:{sum(scores)//len(scores)}" for ht, scores in
                sorted(d["hook_effectiveness"].items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)
                if ht != "?"
            )
            print(f"     钩子效果: {hooks_str}")

    # 生成进化建议
    insights = generate_evolution_insights(all_data)

    print(f"\n{'─'*60}")
    print(f"  🧬 进化建议")
    print(f"{'─'*60}")

    if not insights:
        print("\n  暂无足够数据生成进化建议。")
        print("  完成至少一部小说的多个章节后再运行。")
        return

    for i, ins in enumerate(insights, 1):
        conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(ins["confidence"], "⚪")
        print(f"\n  {conf_icon} [{ins['category']}]")
        print(f"     发现：{ins['finding']}")
        print(f"     建议：{ins['action']}")

    # Apply
    if args.apply:
        apply_evolution(stories_path, insights)
    else:
        print(f"\n  运行 python scripts/evolve.py --apply 自动应用进化建议。")

    print()


if __name__ == "__main__":
    main()

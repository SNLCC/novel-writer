#!/usr/bin/env python3
"""
guide.py — 项目状态诊断与下一步引导

用法:
    python guide.py [--novel <小说目录>]

自动检测当前小说项目的完成度，输出：
- 当前处于哪个阶段
- 已完成什么
- 下一步该做什么
- 对应的脚本命令

首次使用时，如果没有任何小说项目，会引导创建第一部。
"""

import argparse
import re
import sys
from pathlib import Path


from _utils import resolve_stories_root, resolve_novel_path


# ── 路径解析 ────────────────────────────────────────────────

STORY_BIBLE_MARKER = "story-bible.md"


def resolve_novel_path(explicit_path):
    if explicit_path:
        n = Path(explicit_path).resolve()
        if n.exists():
            return n
        return None
    cwd = Path.cwd()
    pf = cwd / ".current-novel"
    if pf.exists():
        n = Path(pf.read_text(encoding="utf-8").strip())
        if n.exists():
            return n.resolve()
    return None


def count_template_placeholders(text):
    """统计 [xxx] 占位符数量，衡量填写完成度"""
    # 排除代码块和表格结构
    placeholders = re.findall(r'\[([^\]]+)\]', text)
    # 过滤掉表格分隔符和纯符号
    meaningful = [p for p in placeholders
                  if p.strip() and not re.match(r'^[-|]+$', p) and len(p.strip()) > 1]
    return len(meaningful)


def check_story_bible(novel_path):
    bible = novel_path / "story-bible.md"
    if not bible.exists():
        return {"status": "missing", "placeholders": 0}

    text = bible.read_text(encoding="utf-8")
    ph_count = count_template_placeholders(text)

    if ph_count == 0:
        return {"status": "complete", "placeholders": 0}
    elif ph_count < 8:
        return {"status": "in_progress", "placeholders": ph_count}
    else:
        return {"status": "empty", "placeholders": ph_count}


def check_outline(novel_path):
    outline_dir = novel_path / "outline"
    master = outline_dir / "master.md"

    if not master.exists():
        return {"status": "missing", "arcs": 0}

    text = master.read_text(encoding="utf-8")
    ph_count = count_template_placeholders(text)

    arcs = list(outline_dir.glob("arc-*.md"))

    if ph_count == 0:
        return {"status": "complete", "arcs": len(arcs)}
    elif ph_count < 10:
        return {"status": "in_progress", "arcs": len(arcs)}
    else:
        return {"status": "empty", "arcs": len(arcs)}


def check_characters(novel_path):
    chars_dir = novel_path / "characters"
    if not chars_dir.exists():
        return {"count": 0, "filled": 0}

    all_files = [f for f in chars_dir.glob("*.md") if f.name != ".gitkeep"]
    filled = 0
    for f in all_files:
        text = f.read_text(encoding="utf-8")
        ph = count_template_placeholders(text)
        if ph < 10:  # 少于 10 个占位符视为已填写
            filled += 1

    return {"count": len(all_files), "filled": filled}


def check_chapters(novel_path):
    chapters_dir = novel_path / "chapters"
    if not chapters_dir.exists():
        return {"total": 0, "completed": 0}

    all_files = [f for f in chapters_dir.glob("ch-*.md")]
    completed = 0
    for f in all_files:
        text = f.read_text(encoding="utf-8")
        if "已完成" in text:
            completed += 1

    return {"total": len(all_files), "completed": completed}


def check_suspense(novel_path):
    sf = novel_path / "notes" / "suspense-tracking.md"
    if not sf.exists():
        return {"status": "missing", "active": 0, "resolved": 0}

    text = sf.read_text(encoding="utf-8")
    active = text.count("未回收") + text.count("部分回收")
    resolved = text.count("已回收")
    ph = count_template_placeholders(text)

    if ph > 5:
        return {"status": "empty", "active": active, "resolved": resolved}
    elif active == 0:
        return {"status": "clean", "active": 0, "resolved": resolved}
    else:
        return {"status": "active", "active": active, "resolved": resolved}


def get_meta(novel_path):
    meta_file = novel_path / "meta.md"
    if not meta_file.exists():
        return {"title": novel_path.name, "type": "?", "status": "?"}
    text = meta_file.read_text(encoding="utf-8")
    info = {"title": novel_path.name, "type": "?", "status": "?"}
    for key, pat in [("title", r'\*\*书名\*\*\s*\|\s*(.+)'),
                      ("type", r'\*\*类型\*\*\s*\|\s*(.+)'),
                      ("status", r'\*\*状态\*\*\s*\|\s*(.+)')]:
        m = re.search(pat, text)
        if m:
            info[key] = m.group(1).strip()
    return info


def find_stories_root(novel_path):
    """从 novel_path 向上找到 stories 根目录"""
    p = novel_path.resolve()
    # novel 目录下应该有 story-bible.md
    if (p / STORY_BIBLE_MARKER).exists():
        return p.parent  # stories 根
    return p


def list_all_novels(stories_root):
    if not stories_root.exists():
        return []
    return sorted([d for d in stories_root.iterdir()
                   if d.is_dir() and not d.name.startswith(".")
                   and (d / STORY_BIBLE_MARKER).exists()])


# ── 主逻辑 ──────────────────────────────────────────────────


def check_skill_version():
    try:
        skill_md = Path(__file__).resolve().parent.parent / 'SKILL.md'
        if skill_md.exists():
            text = skill_md.read_text(encoding='utf-8')
            import re
            m = re.search(r'version:\s*(\S+)', text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return 'unknown'


def diagnose(novel_path, stories_root):
    """全面诊断并输出引导"""
    meta = get_meta(novel_path)
    bible = check_story_bible(novel_path)
    outline = check_outline(novel_path)
    chars = check_characters(novel_path)
    chapters = check_chapters(novel_path)
    suspense = check_suspense(novel_path)
    all_novels = list_all_novels(stories_root)

    # ── 打印状态面板 ──
    print(f"\n{'='*56}")
    print(f"  📖 {meta['title']}")
    print(f"  类型: {meta['type']}  |  状态: {meta['status']}")
    print(f"{'='*56}")

    # 进度条
    items = [
        ("故事圣经", bible["status"]),
        ("全书大纲", outline["status"]),
        ("人物档案", f"{chars['filled']}/{chars['count']}" if chars['count'] > 0 else "无"),
        ("章节进度", f"{chapters['completed']}/{chapters['total']}" if chapters['total'] > 0 else "无"),
        ("悬念追踪", suspense["status"]),
    ]
    for label, val in items:
        icon = "✅" if val in ("complete", "clean") or (isinstance(val, str) and "/" in val and val.split("/")[0] == val.split("/")[1] and val != "0/0") else "⬜"
        if val == "missing":
            icon = "❌"
        elif val == "empty":
            icon = "🟡"
        elif val in ("in_progress", "active"):
            icon = "🟡"
        print(f"  {icon} {label}: {val}")

    # ── 决断下一步 ──
    print(f"\n{'─'*56}")
    print("  📋 下一步建议")
    print(f"{'─'*56}")

    steps = []

    # 阶段判断
    if bible["status"] in ("empty", "missing"):
        steps.append({
            "urgency": "first",
            "title": "填写故事圣经",
            "detail": "世界观、核心规则、家族关系是整部小说的宪法。",
            "cmd": f"编辑 {novel_path.name}/story-bible.md",
            "file": str(novel_path / "story-bible.md"),
        })

    if outline["status"] in ("empty", "missing") and bible["status"] == "complete":
        steps.append({
            "urgency": "first",
            "title": "填写全书大纲",
            "detail": "定义故事梗概、4卷结构、5个核心事件和人物弧线终点。",
            "cmd": f"编辑 {novel_path.name}/outline/master.md",
            "file": str(novel_path / "outline" / "master.md"),
        })

    if outline["status"] == "complete" and chars["count"] == 0:
        steps.append({
            "urgency": "next",
            "title": "创建人物档案",
            "detail": f"大纲中涉及的主要人物需要档案。",
            "cmd": f"python scripts/init_character.py <人物名>",
        })

    # 检查 arc-01 是否需要填写
    arc01 = novel_path / "outline" / "arc-01.md"
    if arc01.exists() and outline["status"] == "complete" and chars["filled"] > 0:
        arc_text = arc01.read_text(encoding="utf-8")
        arc_ph = count_template_placeholders(arc_text)
        if arc_ph > 5:
            steps.append({
                "urgency": "next",
                "title": "填写第一卷大纲 (arc-01.md)",
                "detail": "规划每章的钩子类型、核心冲突、前300字设计。",
                "cmd": f"编辑 {novel_path.name}/outline/arc-01.md",
                "file": str(arc01),
            })

    # 可以开始写章节了
    setup_ready = (
        bible["status"] == "complete"
        and outline["status"] in ("complete", "in_progress")
        and chars["filled"] >= 1
    )
    if setup_ready:
        next_ch = chapters["total"] + 1
        steps.append({
            "urgency": "now",
            "title": f"开始写第 {next_ch} 章",
            "detail": f"设定阶段基本完成，可以开始创作。",
            "cmd": f"python scripts/init_chapter.py {next_ch}",
        })

    # 如果有章节但没悬念记录
    if chapters["total"] > 0 and suspense["status"] == "empty":
        steps.append({
            "urgency": "next",
            "title": "初始化悬念追踪",
            "detail": "章节已开始，但悬念追踪表还是空的。每章写完后记得更新。",
            "cmd": f"python scripts/update_suspense.py --chapter {chapters['total']}",
        })

    # 多卷提示
    if chapters["total"] > 10 and outline["arcs"] < 2:
        steps.append({
            "urgency": "soon",
            "title": "规划第二卷大纲",
            "detail": "已写超过10章，建议准备下一卷的大纲。",
            "cmd": f"python scripts/new_arc.py 2",
        })

    # 一致性检查提示
    if chapters["total"] > 0 and chapters["total"] % 10 == 0:
        steps.append({
            "urgency": "soon",
            "title": "运行一致性检查",
            "detail": f"已写 {chapters['total']} 章，建议做一次全面检查。",
            "cmd": "python scripts/check_consistency.py",
        })

    # 复盘提示
    chapters_dir = novel_path / "chapters"
    total_chs = len(list(chapters_dir.glob("ch-*.md"))) if chapters_dir.exists() else 0
    if total_chs > 0 and total_chs % 10 == 0 and total_chs > 0:
        steps.append({
            "urgency": "soon",
            "title": f"10章复盘（已写 {total_chs} 章）",
            "detail": "运行章节批量复盘，检查质量和节奏。",
            "cmd": "python scripts/review.py --type chapter",
        })

    # 完结小说提示
    meta_file = novel_path / "meta.md"
    if meta_file.exists():
        meta_text = meta_file.read_text(encoding="utf-8")
        if "已完结" in meta_text:
            steps.append({
                "urgency": "now",
                "title": "运行全书复盘 + 同步共享库",
                "detail": "小说已完结！运行复盘沉淀经验，同步模式到共享库。",
                "cmd": "python scripts/review.py --type novel && python scripts/sync_library.py",
            })

    # 多小说提示
    if len(all_novels) > 1:
        current_name = novel_path.name
        others = [n.name for n in all_novels if n.name != current_name]
        if others:
            steps.append({
                "urgency": "info",
                "title": f"其他小说: {', '.join(others)}",
                "detail": "运行 list_novels.py --set <小说名> 切换。",
                "cmd": "python scripts/list_novels.py --path ./stories",
            })

    # 输出步骤
    if not steps:
        print("\n  暂无建议，一切就绪！")
        return

    urgency_order = {"first": 0, "now": 1, "next": 2, "soon": 3, "info": 4}
    steps.sort(key=lambda s: urgency_order.get(s["urgency"], 5))

    for i, s in enumerate(steps, 1):
        tag = {"first": "必须", "now": "现在", "next": "推荐", "soon": "即将", "info": "提示"}.get(s["urgency"], "")
        print(f"\n  [{tag}] {s['title']}")
        print(f"  {s['detail']}")
        print(f"  → {s['cmd']}")

    print()


def main():
    parser = argparse.ArgumentParser(description="项目状态诊断与引导")
    parser.add_argument("--novel", default=None, help="小说项目目录")
    parser.add_argument("--path", default=None, help="stories 根目录（默认自动探测到项目根目录）")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)
    stories_root = resolve_stories_root(args.path)

    # 重新解析：优先 stories_root 下的 .current-novel
    if not novel_path:
        pf = stories_root / ".current-novel"
        if pf.exists():
            n = Path(pf.read_text(encoding="utf-8").strip())
            if n.exists():
                novel_path = n.resolve()

    # 情况1：没有任何小说
    all_novels = list_all_novels(stories_root)
    if not all_novels:
        print("\n  还没有任何小说项目。")
        print(f"  Stories 目录: {stories_root}")
        print(f"\n  创建第一部小说：")
        print(f"  python scripts/new_novel.py <小说名> --path {stories_root}")

        # 检查共享库中是否有经验
        shared_dir = stories_root / ".shared"
        lib_file = shared_dir / "pattern-library.md"
        if lib_file.exists():
            lib_text = lib_file.read_text(encoding="utf-8")
            # 检查是否有实质内容
            if "暂无共享模式" not in lib_text and len(lib_text) > 500:
                print(f"\n  📖 共享库中已有跨项目经验，新项目将自动受益。")
                print(f"     运行 python scripts/evolve.py 查看进化建议。")
        print()
        return

    # 检查共享库
    shared_dir = stories_root / ".shared"
    lib_file = shared_dir / "pattern-library.md"
    shared_insights = []
    if lib_file.exists():
        lib_text = lib_file.read_text(encoding="utf-8")
        # 提取最近的进化建议
        evo_matches = re.findall(r'\[(.+?)\]\s*(.+?)(?=\n\s*→)', lib_text)
        for cat, finding in evo_matches[-3:]:
            shared_insights.append(f"{cat}: {finding[:60]}")

    # 情况2：有小说但没指定当前
    if not novel_path:
        print(f"\n  找到 {len(all_novels)} 部小说，但没有设置「当前小说」。")
        if shared_insights:
            print(f"\n  📖 共享库最近洞察：")
            for si in shared_insights:
                print(f"     • {si}")
        print(f"\n  请选择：")
        for n in all_novels:
            print(f"  python scripts/list_novels.py --path {stories_root} --set {n.name}")
        print()
        return

    # 情况3：正常诊断
    if shared_insights:
        print(f"\n  📖 共享库洞察（跨项目经验）：")
        for si in shared_insights:
            print(f"     • {si}")
    # 显示 skill 版本
    skill_ver = check_skill_version()
    print(f'  Skill 版本: v{skill_ver}')

    # 检查是否有共享数据
    shared_dir = stories_root / '.shared'
    if shared_dir.exists():
        pf = shared_dir / 'platform-data.md'
        if pf.exists():
            pf_text = pf.read_text(encoding='utf-8')
            if '用户提供' not in pf_text and len(pf_text) > 300:
                print(f'  [INFO] 已加载用户积累的平台数据')

    diagnose(novel_path, stories_root)


if __name__ == "__main__":
    main()

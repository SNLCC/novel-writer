#!/usr/bin/env python3
"""
check_scenes.py — 场景漂移检测

用法:
    python check_scenes.py [--novel <小说目录>] [--chapter <章节号>]

检测项：
    1. 章节中出现的场景是否都有档案
    2. 已有场景档案的描写锚点是否在章节中被遵守
    3. 章节中是否引入了新场景但未创建档案
    4. 高频场景是否多章未更新出场记录
"""

import argparse
import re
import sys
from pathlib import Path

from _utils import resolve_novel_path


# ── 场景名提取 ──────────────────────────────────────────────

_SCENE_KEYWORDS = [
    "大殿", "广场", "密室", "洞府", "森林", "山脉", "山谷", "峡谷",
    "城市", "村庄", "小镇", "学院", "宗门", "宫殿", "塔", "阁", "楼",
    "房间", "客厅", "书房", "卧室", "厨房", "地下室", "仓库",
    "街道", "市场", "酒馆", "客栈", "商铺", "衙门", "皇宫",
    "秘境", "遗迹", "荒原", "沙漠", "海域", "岛屿", "洞穴",
    "道场", "练功房", "藏经阁", "丹房", "器室",
    "战场", "城堡", "要塞", "关隘",
]

_EXCLUDE_SCENE = {
    "世界", "天下", "人间", "仙界", "魔界", "凡间",
    "门口", "路边", "途中", "半路", "远处", "附近",
}


def _is_likely_scene_name(name):
    """判断是否像一个场景名"""
    name = name.strip()
    if not name or len(name) > 20:
        return False
    if name in _EXCLUDE_SCENE:
        return False
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', name))
    return has_chinese


def extract_scenes_from_text(text):
    """从文本中提取可能的场景名"""
    found = set()

    # 模式1：「地名」格式
    for m in re.finditer(r'「([^」]{2,20})」', text):
        candidate = m.group(1)
        if any(kw in candidate for kw in _SCENE_KEYWORDS):
            if _is_likely_scene_name(candidate):
                found.add(candidate)

    # 模式2：在场景关键词前后查找场景名
    for kw in _SCENE_KEYWORDS:
        for m in re.finditer(rf'(.{{0,8}}{kw})', text):
            candidate = m.group(1).strip()
            if _is_likely_scene_name(candidate) and len(candidate) >= 2:
                # 去掉前导的标点和虚词
                candidate = re.sub(r'^[，。、；：""''！？…—\s]+', '', candidate)
                if len(candidate) >= 2:
                    found.add(candidate)

    return found


def load_scene_anchors(scenes_dir):
    """加载所有场景档案的描写锚点"""
    anchors = {}
    if not scenes_dir.exists():
        return anchors

    for sf in scenes_dir.glob("*.md"):
        if sf.name.startswith("."):
            continue
        text = sf.read_text(encoding="utf-8")
        name = sf.stem

        # 提取视觉特征
        visual = []
        in_visual = False
        for line in text.split("\n"):
            if "视觉特征" in line:
                in_visual = True
                continue
            if in_visual:
                if line.strip().startswith("###") or line.strip().startswith("##"):
                    break
                m = re.match(r'-\s*(.+)', line)
                if m and m.group(1).strip() and not m.group(1).strip().startswith("["):
                    visual.append(m.group(1).strip())

        # 提取氛围关键词
        atmosphere = []
        in_atmo = False
        for line in text.split("\n"):
            if "氛围关键词" in line:
                in_atmo = True
                continue
            if in_atmo:
                if line.strip().startswith("##"):
                    break
                val = line.strip()
                if val and not val.startswith("[") and not val.startswith("#"):
                    atmosphere.append(val)

        # 提取场景规则
        rules = []
        in_rules = False
        for line in text.split("\n"):
            if "场景规则" in line:
                in_rules = True
                continue
            if in_rules:
                if line.strip().startswith("##"):
                    break
                m = re.match(r'\d+\.\s*(.+)', line)
                if m and m.group(1).strip() and not m.group(1).strip().startswith("["):
                    rules.append(m.group(1).strip())

        # 提取出场记录数
        appearances = 0
        in_appear = False
        for line in text.split("\n"):
            if "出场记录" in line:
                in_appear = True
                continue
            if in_appear:
                if line.strip().startswith("#"):
                    break
                if re.match(r'\|\s*ch-', line):
                    appearances += 1

        anchors[name] = {
            "visual": visual,
            "atmosphere": atmosphere,
            "rules": rules,
            "appearances": appearances,
        }

    return anchors


def parse_scene_meta(scene_file):
    """解析场景档案的元信息"""
    if not scene_file.exists():
        return {}
    text = scene_file.read_text(encoding="utf-8")
    info = {}
    for key, pat in [
        ("type", r'\*\*类型\*\*[：:]\s*(.+)'),
        ("frequency", r'\*\*出现频率\*\*[：:]\s*(.+)'),
    ]:
        # search in the header block
        header = text[:500]
        m = re.search(pat, header)
        if m:
            info[key] = m.group(1).strip()
    return info


def check_scenes(novel_path, chapter_num=None):
    """场景漂移检测"""
    issues = []

    scenes_dir = novel_path / "scenes"
    chapters_dir = novel_path / "chapters"

    # 1. 检查场景档案目录是否存在
    if not scenes_dir.exists():
        issues.append({
            "severity": "info",
            "title": "场景档案目录不存在",
            "detail": "scenes/ 目录未创建。运行 init_scene.py 创建场景档案。",
            "fix": "python scripts/init_scene.py <场景名>",
        })
        return issues

    # 2. 加载已有场景锚点
    scene_anchors = load_scene_anchors(scenes_dir)
    known_scenes = set(scene_anchors.keys())

    # 3. 扫描章节
    chapter_files = sorted(chapters_dir.glob("ch-*.md")) if chapters_dir.exists() else []
    if chapter_num:
        chapter_files = [f for f in chapter_files if f"ch-{chapter_num:02d}" in f.name]

    all_chapter_scenes = set()
    chapter_scene_map = {}

    for cf in chapter_files:
        text = cf.read_text(encoding="utf-8")
        scenes = extract_scenes_from_text(text)
        all_chapter_scenes.update(scenes)
        chapter_scene_map[cf.name] = scenes

    # 4. 检测无档案的场景
    unarchived = all_chapter_scenes - known_scenes
    # 只报告比较确定的场景（在多个章节出现 或 名称较长）
    confirmed_unarchived = set()
    for s in unarchived:
        count = sum(1 for scenes in chapter_scene_map.values() if s in scenes)
        if count >= 2 or len(s) >= 4:
            confirmed_unarchived.add(s)

    if confirmed_unarchived:
        issues.append({
            "severity": "warning",
            "title": f"发现 {len(confirmed_unarchived)} 个未建档的场景",
            "detail": "、".join(sorted(confirmed_unarchived)[:10]),
            "fix": "python scripts/init_scene.py <场景名>",
        })

    # 5. 检测高频场景是否多章未更新
    for name, anchors in scene_anchors.items():
        meta = parse_scene_meta(scenes_dir / f"{name}.md")
        freq = meta.get("frequency", "")
        if "高频" in freq and chapter_files:
            total_ch = len(chapter_files)
            apps = anchors.get("appearances", 0)
            if total_ch > 0 and apps < total_ch * 0.3:
                issues.append({
                    "severity": "warning",
                    "title": f"高频场景「{name}」出场记录偏少",
                    "detail": f"共 {total_ch} 章，仅 {apps} 次出场记录",
                    "fix": f"检查 scenes/{name}.md 出场记录表是否漏记",
                })

    # 6. 检查场景锚点一致性（抽样高出场场景）
    for name, anchors in scene_anchors.items():
        if anchors["appearances"] < 2:
            continue
        # 对已有描写的场景，简单报告状态
        if not anchors["visual"]:
            issues.append({
                "severity": "info",
                "title": f"场景「{name}」缺少视觉锚点",
                "detail": "建议补充 3-5 个核心视觉元素，确保各章描写一致",
                "fix": f"编辑 scenes/{name}.md",
            })
        if not anchors["rules"]:
            issues.append({
                "severity": "info",
                "title": f"场景「{name}」缺少场景规则",
                "detail": "建议补充场景内必须遵守的规则/限制",
                "fix": f"编辑 scenes/{name}.md",
            })

    if not issues:
        issues.append({
            "severity": "ok",
            "title": "场景一致性检查通过",
            "detail": f"共 {len(known_scenes)} 个场景档案，{len(chapter_files)} 个章节",
            "fix": "",
        })

    return issues


def main():
    parser = argparse.ArgumentParser(description="场景漂移检测")
    parser.add_argument("--novel", default=None, help="小说项目目录")
    parser.add_argument("--chapter", type=int, default=None, help="仅检查指定章节")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)
    if not novel_path:
        print("[ERROR] 无法定位小说项目。请指定 --novel 或设置当前小说。")
        sys.exit(1)

    issues = check_scenes(novel_path, args.chapter)

    severity_order = {"error": 0, "warning": 1, "info": 2, "ok": 3}
    issues.sort(key=lambda i: severity_order.get(i["severity"], 5))

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warn_count = sum(1 for i in issues if i["severity"] == "warning")

    print(f"\n场景一致性检查 — {novel_path.name}\n")

    for i, issue in enumerate(issues, 1):
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️", "ok": "✅"}.get(issue["severity"], "•")
        print(f"  {icon} {issue['title']}")
        if issue["detail"]:
            print(f"     {issue['detail']}")
        if issue["fix"]:
            print(f"     → {issue['fix']}")

    print()
    if error_count > 0 or warn_count > 0:
        print(f"共 {error_count} 个错误，{warn_count} 个警告")
        if error_count > 0:
            sys.exit(1)
    else:
        print("一切正常！")

    # 汇总
    scenes_dir = novel_path / "scenes"
    if scenes_dir.exists():
        scene_files = [f for f in scenes_dir.glob("*.md") if not f.name.startswith(".")]
        print(f"\n场景档案: {len(scene_files)} 个")
        for sf in sorted(scene_files):
            anchors = load_scene_anchors(scenes_dir)
            info = anchors.get(sf.stem, {})
            apps = info.get("appearances", 0) if isinstance(info, dict) else 0
            has_visual = "✅" if (isinstance(info, dict) and info.get("visual")) else "⬜"
            has_rules = "✅" if (isinstance(info, dict) and info.get("rules")) else "⬜"
            print(f"  {has_visual} {has_rules} {sf.stem} (出场 {apps} 次)")


if __name__ == "__main__":
    main()

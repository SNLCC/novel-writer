#!/usr/bin/env python3
"""
init_scene.py — 初始化场景档案

用法:
    python init_scene.py <场景名> [--novel <小说目录>] [--type <场景类型>]

自动检测当前小说项目，创建 scenes/<场景名>.md 档案文件。
"""

import argparse
import sys
from pathlib import Path


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


TEMPLATE = """# 场景：{name}

> **类型**：[室内 / 室外 / 建筑 / 自然环境 / 城市 / 秘境 / 其他]
> **首次出现**：[章节]
> **关联人物**：[人物列表]

---

## 一、基础信息

| 字段 | 内容 |
|------|------|
| **场景名称** | {name} |
| **地理位置** | [所属地区 / 坐标] |
| **时代** | [年代 / 时期] |
| **类型** | [{scene_type}] |
| **规模** | [面积 / 容量 / 尺度] |

---

## 二、场景描写锚点（不可随意变动的核心特征）

### 2.1 视觉特征（3-5 个核心元素）
- [核心视觉元素 1]
- [核心视觉元素 2]
- [核心视觉元素 3]

### 2.2 感官特征
- **声音**：[环境音 / 标志性声音]
- **气味**：[特有的气味]
- **触感/温度**：[温度 / 湿度 / 质感]

### 2.3 氛围关键词
[3-5 个形容该场景氛围的词]

---

## 三、功能属性

- **故事功能**：[聚会 / 战斗 / 藏匿 / 交易 / 修炼 / 日常 / ...]
- **叙事价值**：[推动情节 / 人物发展 / 世界观展示 / 氛围营造]
- **出现频率**：[高频 / 中频 / 低频 / 一次性]

---

## 四、场景规则

> 在该场景中必须遵守的规则 / 限制 / 特性

1. [规则 1]
2. [规则 2]
3. [规则 3]

---

## 五、场景内的关键道具

| 道具 | 位置 | 用途 | 首次提及章 |
|------|------|------|-----------|
|      |      |      |           |

---

## 六、出场记录

| 章节 | 关键事件 | 场景状态变化 | 描写一致性检查 |
|------|----------|-------------|---------------|
|      |          |             | ✅ / ⚠️ 需修正 |

---

> **更新规则**：每次写到该场景后，如有描写变化 / 新增元素 / 状态改变，必须同步更新本档案。
"""


def create_scene(novel_path: Path, name: str, scene_type: str):
    scenes_dir = novel_path / "scenes"
    scenes_dir.mkdir(exist_ok=True)

    filename = f"{name}.md"
    scene_file = scenes_dir / filename

    if scene_file.exists():
        print(f"[WARN] 场景档案已存在: {scene_file}")
        response = input("  覆盖？(y/N): ").strip().lower()
        if response != 'y':
            print("  已取消。")
            return

    content = TEMPLATE.format(name=name, scene_type=scene_type or "待定")
    scene_file.write_text(content, encoding="utf-8")
    print(f"[OK] 创建场景档案: {scene_file}")
    print(f"  场景名: {name}")
    print(f"  类型: {scene_type or '待定'}")
    print(f"\n请编辑 {scene_file} 填写详细设定。")


def main():
    parser = argparse.ArgumentParser(description="初始化场景档案")
    parser.add_argument("name", help="场景名称")
    parser.add_argument("--novel", default=None, help="小说项目目录（默认自动检测）")
    parser.add_argument("--type", default=None, help="场景类型（室内/室外/建筑/自然环境/城市/秘境/其他）")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)

    if not (novel_path / "story-bible.md").exists():
        print(f"[WARN] 未找到 story-bible.md，这可能不是小说项目目录")
        print(f"  路径: {novel_path}")

    create_scene(novel_path, args.name, args.type)


if __name__ == "__main__":
    main()

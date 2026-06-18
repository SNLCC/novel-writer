#!/usr/bin/env python3
"""
init_character.py — 初始化新人物档案

用法:
    python init_character.py <人物名> [--novel <小说目录>]

如果不指定 --novel，自动读取 .current-novel 或使用当前目录。
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


TEMPLATE = """# {name}

> **身份**：[主角 / 配角 / 反派 / 导师 / 恋人 / 其他]
> **首次出场**：[章节]
> **状态**：存活 / 已死亡 / 未知

---

## 一、基础信息

| 字段 | 内容 |
|------|------|
| **姓名** | {name} |
| **年龄** | [年龄] |
| **性别** | [性别] |
| **外貌** | [身高/体型/特征] |
| **身份/职业** | [身份] |
| **性格关键词** | [3-5个词] |

---

## 二、深层设定

### 2.1 背景故事
[过往经历 / 创伤 / 执念]

### 2.2 核心欲望（Want）
[角色想要什么——表面的、具体的]

### 2.3 深层需求（Need）
[角色真正需要什么——内在的、角色自己可能不知道的]

### 2.4 致命缺陷
[什么阻碍他/她得到真正需要的东西]

### 2.5 优势/天赋
[他/她擅长什么]

---

## 三、关系网络

| 关系对象 | 关系类型 | 动态描述 |
|----------|----------|----------|
| [人物A] | [师徒/敌对/恋人/...] | [关系如何变化] |
|          |          |          |

---

## 四、人物弧线

| 阶段 | 对应卷/章 | 人物状态 | 关键转变 |
|------|-----------|----------|----------|
| 起点 | ch-XX | [初始状态] | — |
| 成长 | ch-XX ~ ch-XX | [变化过程] | [什么事件触发变化] |
| 转折 | ch-XX | [关键转折] | [转变内容] |
| 终点 | ch-XX | [最终状态] | [结果] |

---

## 五、行为一致性规则

- **说话风格**：[口头禅 / 语气 / 用词习惯]
- **决策模式**：[遇到问题时的典型反应]
- **底线/禁忌**：[绝不能做的事]
- **情感触发点**：[什么会让他/她失控]

---

## 六、出场记录

| 章节 | 关键行为 | 弧线进度 | 备注 |
|------|----------|----------|------|
|      |          |          |      |

---

> **更新规则**：每次章节完成后，如该人物有行为/关系/状态变化，必须同步更新本档案。
"""


def create_character(novel_path: Path, name: str):
    characters_dir = novel_path / "characters"
    characters_dir.mkdir(exist_ok=True)

    filename = f"{name}.md"
    char_file = characters_dir / filename

    if char_file.exists():
        print(f"[WARN] 人物档案已存在: {char_file}")
        response = input("  覆盖？(y/N): ").strip().lower()
        if response != 'y':
            print("  已取消。")
            return

    content = TEMPLATE.format(name=name)
    char_file.write_text(content, encoding="utf-8")
    print(f"[OK] 创建人物档案: {char_file}")
    print(f"\n请编辑 {char_file} 填写详细设定。")


def main():
    parser = argparse.ArgumentParser(description="初始化新人物档案")
    parser.add_argument("name", help="人物名称")
    parser.add_argument("--novel", default=None, help="小说项目目录（默认自动检测）")
    args = parser.parse_args()

    novel_path = resolve_novel_path(args.novel)

    if not (novel_path / "story-bible.md").exists():
        print(f"[WARN] 未找到 story-bible.md，这可能不是小说项目目录")
        print(f"  路径: {novel_path}")

    create_character(novel_path, args.name)


if __name__ == "__main__":
    main()

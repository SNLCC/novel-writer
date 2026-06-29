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
from _utils import resolve_novel_path


# ── 路径解析 ────────────────────────────────────────────────
# resolve_novel_path 已由 _utils 模块统一管理


TEMPLATE = """# {name}

> **身份**：[主角 / 配角 / 反派 / 导师 / 恋人 / 其他]
> **首次出场**：[章节]
> **状态**：[存活 / 已死亡 / 未知]
> **最后更新**：[YYYY-MM-DD]

---

## 一、基础信息

| 字段 | 内容 |
|------|------|
| **姓名** | {name} |
| **别名/称号** | [如有] |
| **年龄** | [年龄] |
| **性别** | [性别] |
| **身高/体型** | [身高 / 体型特征] |
| **外貌特征** | [3-5 个不可忘记的特征] |
| **身份/职业** | [当前身份] |
| **性格关键词** | [3-5 个词] |

---

## 二、出生背景

| 字段 | 内容 |
|------|------|
| **出生年代** | [年代 / 纪元] |
| **出生地** | [地点] |
| **家族背景** | [家族 / 出身 / 阶层] |
| **童年经历** | [关键童年事件] |
| **成长环境** | [环境描述] |

---

## 三、深层设定

### 3.1 核心欲望（Want）
[角色想要什么——表面的、具体的、角色自己知道的]

### 3.2 深层需求（Need）
[角色真正需要什么——内在的、角色自己可能不知道的]

### 3.3 致命缺陷（Flaw）
[什么阻碍他/她得到真正需要的东西——性格/认知上的缺陷]

### 3.4 优势/天赋
[他/她擅长什么]

### 3.5 核心创伤
[过去的关键创伤事件，驱动当前行为]

---

## 四、关系网络

| 关系对象 | 关系类型 | 初始状态 | 当前状态 | 关键转折章节 | 动态描述 |
|----------|----------|----------|----------|-------------|----------|
| [人物A] | [师徒/敌对/恋人/朋友/亲人/同门/陌生] | [初始] | [当前] | ch-XX | [关系如何演变] |
|          |          |          |          |             |          |

---

## 五、人物弧线

| 阶段 | 对应卷/章 | 人物状态 | 关键转变 |
|------|-----------|----------|----------|
| **起点** | ch-XX | [初始状态——让读者看到缺陷] | — |
| **成长** | ch-XX ~ ch-XX | [变化过程——让读者看到挣扎] | [什么事件触发变化] |
| **转折** | ch-XX | [关键转折——让读者看到第一缕光] | [转变内容] |
| **终点** | ch-XX | [最终状态——让读者感到「值了」] | [结果] |

---

## 六、行为一致性规则

| 规则类别 | 具体内容 |
|----------|----------|
| **说话风格** | [口头禅 / 语气 / 用词习惯] |
| **决策模式** | [遇到问题时的典型反应] |
| **底线/禁忌** | [绝不能做的事] |
| **情感触发点** | [什么会让他/她失控] |
| **习惯/小动作** | [标志性肢体语言] |

---

## 七、关键行为记录

> 📌 随故事推进逐章补充。记录角色的重要行为、决策、变化。

| 章节 | 关键行为/决策 | 行为动机 | 弧线进度 | 备注 |
|------|-------------|----------|----------|------|
|      |             |          |          |      |

---

## 八、出场记录

| 章节 | 出场场景 | 关键行为 | 弧线进度 | 备注 |
|------|----------|----------|----------|------|
|      |          |          |          |      |

---

> **更新规则**：
> - 每次章节完成后，如该人物有行为/关系/状态变化，必须同步更新本档案。
> - 「关键行为记录」表随章节推进逐章补充。
> - 「关系网络」表中的「当前状态」和「关键转折章节」列实时更新。
> - 人物弧线终点不可擅改，路径可调整。
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

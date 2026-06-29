#!/usr/bin/env python3
"""
_utils.py — Novel Writer Skill 共享工具模块

集中管理：
- 项目根目录自动探测（解决 .codex 只读问题）
- 默认 stories 路径生成
- novel 路径解析（替代各脚本重复的 resolve_novel_path）
"""

import os
import sys
from pathlib import Path
from typing import Optional


# ── 项目根目录探测 ──────────────────────────────────────────


def find_project_root(cwd: Optional[Path] = None) -> Path:
    """
    从当前目录向上遍历，寻找项目根目录。

    策略（按优先级）：
    1. 查找 .reasonix/ 目录（Codex Desktop 项目标记，最可靠）
    2. 查找 .git/ 目录（取最上层的那个，避免被子模块/嵌套仓库干扰）
    3. 如果都没找到，回退到 cwd

    在 Codex Desktop 中，项目根目录下必有 .reasonix/。
    在独立 Git 仓库中，.git 标记根目录。
    """
    if cwd is None:
        cwd = Path.cwd()

    current = cwd.resolve()
    best = current  # fallback

    # 第一遍：找 .reasonix
    while True:
        if (current / ".reasonix").exists():
            return current
        if current.parent == current:
            break
        current = current.parent

    # 第二遍：找最上层的 .git（避免被子模块内的 .git 拦截）
    current = cwd.resolve()
    git_root = None
    while True:
        if (current / ".git").exists():
            git_root = current
        if current.parent == current:
            break
        current = current.parent

    return git_root if git_root else best


def default_stories_path(cwd: Optional[Path] = None) -> Path:
    """
    返回默认的 stories 目录路径。

    优先级：
    1. CODEX_STORIES_PATH 环境变量（若设定了则直接使用）
    2. 项目根目录下的 stories/

    Codex 环境下，项目根目录 = 用户 workspace（可写），因此
    stories/ 会创建在 workspace 下，而非 .codex 只读目录内。
    """
    env_path = os.environ.get("CODEX_STORIES_PATH")
    if env_path:
        return Path(env_path).resolve()

    project_root = find_project_root(cwd)
    return project_root / "stories"


# ── Novel 路径解析 ──────────────────────────────────────────

def resolve_novel_path(
    explicit_path: Optional[str] = None,
    stories_root: Optional[Path] = None,
) -> Path:
    """
    解析小说项目目录路径，替代各脚本中重复的 resolve_novel_path()。

    解析优先级：
    1. explicit_path 显式指定 → 直接使用
    2. .current-novel 指针文件 → 读取指针指向的目录
    3. 回退到 stories_root（默认通过 find_project_root 得到）

    Args:
        explicit_path: 用户通过 --novel 传入的路径
        stories_root:  stories 根目录（默认自动探测）

    Returns:
        解析后的小说目录 Path（调用者需自行 .exists() 检查）
    """
    if explicit_path:
        novel_path = Path(explicit_path).resolve()
        return novel_path

    if stories_root is None:
        stories_root = default_stories_path()

    pointer_file = stories_root / ".current-novel"
    if pointer_file.exists():
        target = pointer_file.read_text(encoding="utf-8").strip()
        novel_path = Path(target)
        if novel_path.exists():
            return novel_path.resolve()

    # 如果 pointer 不存在或不可读，退回 stories_root 自身
    return stories_root


def require_novel_path(
    explicit_path: Optional[str] = None,
    stories_root: Optional[Path] = None,
) -> Path:
    """
    同 resolve_novel_path，但若无法定位则报错退出。

    用于 validate_preflight 等需要确保必找到小说的脚本。
    """
    novel_path = resolve_novel_path(explicit_path, stories_root)
    if not novel_path.exists() or not (novel_path / "story-bible.md").exists():
        stories = stories_root or default_stories_path()
        print(f"[ERROR] 无法定位小说项目。")
        print(f"  请指定 --novel <小说目录> 或设置 .current-novel 指针。")
        print(f"  当前 stories 根目录: {stories}")
        sys.exit(1)
    return novel_path


# ── Stories 根目录解析（用于 new_novel / list_novels / guide 等）─

def resolve_stories_root(explicit_path: Optional[str] = None) -> Path:
    """
    解析 stories 根目录。

    1. 如果用户通过 --path 显式指定，使用该路径
    2. 否则自动探测项目根目录下的 stories/
    """
    if explicit_path:
        return Path(explicit_path).resolve()
    return default_stories_path()


# ── 模板路径 ────────────────────────────────────────────────

def get_template_path(custom_path: Optional[str] = None) -> Path:
    """
    获取 novel 创建模板路径。

    1. 如果用户通过 --template 指定，使用该路径
    2. 否则从脚本所在目录向上查找 assets/novel-template/
    """
    if custom_path:
        return Path(custom_path).resolve()

    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "assets" / "novel-template"

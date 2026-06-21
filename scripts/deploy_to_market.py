#!/usr/bin/env python3
"""
将 webnovel-writer 的 8 个子技能部署到 Marvis skills/market/ 层，使它们出现在 "/" 斜杠菜单中。

路径调整规则：
  {SKILL_ROOT}/scripts/         → {SKILL_ROOT}/../webnovel-writer/scripts/
  {SKILL_ROOT}/../../references/ → {SKILL_ROOT}/../webnovel-writer/references/
  {SKILL_ROOT}/../../templates/  → {SKILL_ROOT}/../webnovel-writer/templates/
  {SKILL_ROOT}/../../*           → {SKILL_ROOT}/../webnovel-writer/*
"""

import os
import json
import shutil
import re
from pathlib import Path

SKILL_MARKET = Path("/Users/houjiale/Library/Application Support/com.tencent.mac.marvis/MarvisData/User/oAN1i2QEZTXoWZ2fQI7MzTbUyjIQ/skills/market")
WRITER_ROOT = SKILL_MARKET / "webnovel-writer"
SUBSKILLS_DIR = WRITER_ROOT / "skills"
DESKTOP_CLONE = Path("/Users/houjiale/Desktop/webnovel-writer-marvis-clone")

SUB_SKILLS = [
    "webnovel-dashboard",
    "webnovel-doctor",
    "webnovel-init",
    "webnovel-learn",
    "webnovel-plan",
    "webnovel-query",
    "webnovel-review",
    "webnovel-write",
]

# Path adjustments: (pattern, replacement) — order matters, more specific first
PATH_ADJUSTMENTS = [
    # parent-level shared resources (../../ is relative from skills/<sub-skill>/ to webnovel-writer/)
    ("{SKILL_ROOT}/../../references/", "{SKILL_ROOT}/../webnovel-writer/references/"),
    ("{SKILL_ROOT}/../../templates/", "{SKILL_ROOT}/../webnovel-writer/templates/"),
    # shared scripts (need to go up from market-level to webnovel-writer/)
    ("{SKILL_ROOT}/scripts/", "{SKILL_ROOT}/../webnovel-writer/scripts/"),
    ("{SKILL_ROOT}/scripts", "{SKILL_ROOT}/../webnovel-writer/scripts"),
]


def deploy_one(skill_name: str) -> bool:
    target_dir = SKILL_MARKET / skill_name
    source_dir = SUBSKILLS_DIR / skill_name
    desktop_source_dir = DESKTOP_CLONE / "skills" / skill_name

    if not source_dir.is_dir():
        print(f"  [SKIP] {skill_name}: source dir not found at {source_dir}")
        return False

    # Read original SKILL.md from desktop clone (authoritative source)
    desktop_skill_md = desktop_source_dir / "SKILL.md"
    if not desktop_skill_md.is_file():
        print(f"  [SKIP] {skill_name}: SKILL.md not found at {desktop_skill_md}")
        return False

    original_content = desktop_skill_md.read_text(encoding="utf-8")

    # Apply path adjustments
    adjusted = original_content
    for old, new in PATH_ADJUSTMENTS:
        adjusted = adjusted.replace(old, new)

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Write adjusted SKILL.md
    (target_dir / "SKILL.md").write_text(adjusted, encoding="utf-8")

    # Symlink all other files/dirs from the source to preserve local references
    for item in source_dir.iterdir():
        if item.name == "SKILL.md":
            continue  # Already written above
        target = target_dir / item.name
        if target.exists() or target.is_symlink():
            continue
        if item.is_dir():
            os.symlink(item.resolve(), target, target_is_directory=True)
        else:
            os.symlink(item.resolve(), target)

    # Create _meta.json if not exists
    meta_path = target_dir / "_meta.json"
    if not meta_path.exists():
        meta = {
            "ownerId": "local",
            "slug": skill_name,
            "version": "1.0.18",
            "publishedAt": 1781943297775,
        }
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Symlink shared resources from parent webnovel-writer
    _symlink_shared(target_dir, skill_name)

    print(f"  [OK] {skill_name} deployed to {target_dir}")
    return True


def _symlink_shared(target_dir: Path, skill_name: str):
    """Symlink parent-level shared resources that sub-skills need."""
    PARENT = target_dir.parent / "webnovel-writer"

    # parent references: needed by webnovel-plan, webnovel-query
    refs_needed = {"webnovel-plan", "webnovel-query"}
    if skill_name in refs_needed:
        link = target_dir / "parent-references"
        if not link.exists():
            os.symlink((PARENT / "references").resolve(), link, target_is_directory=True)

    # templates: needed by webnovel-plan
    if skill_name == "webnovel-plan":
        link = target_dir / "templates"
        if not link.exists():
            os.symlink((PARENT / "templates").resolve(), link, target_is_directory=True)


def main():
    print("Deploying webnovel-writer sub-skills to market level...\n")
    ok = 0
    for name in SUB_SKILLS:
        if deploy_one(name):
            ok += 1
    print(f"\nDone: {ok}/{len(SUB_SKILLS)} deployed successfully.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plan commit CLI — 原子规划提交链。

单次调用自动执行：占位扫描 → 总纲写回 → 刷新 Story System 合同 → 更新投影状态 → 运行日志 → 最终报告。
外部无需再分别调用 placeholder-scan / master-outline-sync / story-system / update-state / run-log / user-report，物理杜绝漏跑。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio

from data_modules.user_report import build_user_report, format_user_report
from data_modules.run_logger import write_run_log

_SCRIPT_DIR = Path(__file__).resolve().parent


def _die(stage: str, errors: list[str]) -> None:
    print(json.dumps({"blocked": True, "stage": stage, "errors": errors}, ensure_ascii=False, indent=2), file=sys.stderr)
    sys.exit(1)


def _run_script(script_name: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(_SCRIPT_DIR / script_name), *args],
        capture_output=True, text=True,
    )


def _parse_chapter_range(raw: str) -> list[int]:
    """Parse '1-50' into list of ints [1, 2, ..., 50]."""
    start, _, end = raw.partition("-")
    try:
        s = int(start)
        e = int(end) if end else s
        if e < s:
            raise ValueError("end < start")
        return list(range(s, e + 1))
    except Exception as exc:
        raise SystemExit(f"invalid chapter range '{raw}': {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan commit CLI（原子规划提交链）")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--volume", type=int, required=True, help="卷号")
    parser.add_argument("--chapters-range", required=True, help="章节范围，如 1-50")
    parser.add_argument("--writeback-file", default="", help="总纲写回 JSON 文件路径")
    parser.add_argument("--genre", default="", help="题材（用于 story-system）")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    volume = args.volume
    chapters = _parse_chapter_range(args.chapters_range)

    # ── 1. 占位扫描 ──
    try:
        _run_script("placeholder_scanner.py", [
            "--project-root", str(project_root),
            "--format", "text",
        ])
    except Exception as exc:
        print(f"⚠️  占位扫描失败（非致命）: {exc}", file=sys.stderr)

    # ── 2. 总纲写回（master-outline-sync） ──
    try:
        sync_args = [
            "--project-root", str(project_root),
            "--volume", str(volume),
            "--format", "text",
        ]
        if args.writeback_file:
            sync_args.extend(["--writeback-file", args.writeback_file])
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(_SCRIPT_DIR / "update_master_outline.py"), *sync_args],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"⚠️  总纲写回失败: {result.stderr.strip()}", file=sys.stderr)
    except Exception as exc:
        print(f"⚠️  总纲写回失败（非致命）: {exc}", file=sys.stderr)

    # ── 3. 刷新 Story System 合同（逐章） ──
    genre = args.genre
    if not genre:
        try:
            state = json.loads((project_root / ".webnovel" / "state.json").read_text(encoding="utf-8"))
            pi = state.get("project_info", {})
            genre = pi.get("genre") or state.get("project", {}).get("genre", "")
        except Exception:
            pass

    contract_ok = 0
    contract_fail = 0
    for ch in chapters:
        try:
            # 解析章纲目标
            outline_path = project_root / "大纲" / f"第{volume}卷-详细大纲.md"
            chapter_goal = f"第{ch}章"
            if outline_path.exists():
                text = outline_path.read_text(encoding="utf-8")
                # Try to find chapter goal from the outline
                for line in text.splitlines():
                    if f"## 第{ch}章" in line or f"## 第{ch} " in line:
                        chapter_goal = line.strip().lstrip("#").strip()
                        break

            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(_SCRIPT_DIR / "story_system.py"),
                 chapter_goal,
                 "--project-root", str(project_root),
                 "--genre", genre,
                 "--chapter", str(ch),
                 "--persist",
                 "--emit-runtime-contracts",
                 "--format", "both"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                contract_ok += 1
            else:
                contract_fail += 1
                print(f"  ⚠️  第{ch}章合同刷新失败: {result.stderr.strip()[:120]}", file=sys.stderr)
        except Exception as exc:
            contract_fail += 1
            print(f"  ⚠️  第{ch}章合同刷新异常: {exc}", file=sys.stderr)

    # ── 4. 更新投影状态 ──
    try:
        _run_script("update_state.py", [
            "--project-root", str(project_root),
            "--volume-planned", str(volume),
            "--chapters-range", args.chapters_range,
        ])
    except Exception as exc:
        print(f"⚠️  投影状态更新失败（非致命）: {exc}", file=sys.stderr)

    # ── 5. 运行日志 ──
    try:
        write_run_log(
            project_root,
            event="plan_commit",
            payload={
                "volume": volume,
                "chapters_range": args.chapters_range,
                "contracts_ok": contract_ok,
                "contracts_fail": contract_fail,
            },
        )
    except Exception as exc:
        print(f"⚠️  运行日志写入失败（非致命）: {exc}", file=sys.stderr)

    # ── 6. 最终报告（user_report） ──
    report_text = ""
    try:
        report = build_user_report(project_root, stage="plan", volume=volume)
        report_text = format_user_report(report, "text")
    except Exception as exc:
        print(f"⚠️  最终报告生成失败（非致命）: {exc}", file=sys.stderr)

    print(json.dumps({
        "volume": volume,
        "chapters_range": args.chapters_range,
        "contracts_ok": contract_ok,
        "contracts_fail": contract_fail,
        "_user_report": report_text,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.platform == "win32":
        enable_windows_utf8_stdio()
    main()

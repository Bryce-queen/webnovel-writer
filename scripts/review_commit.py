#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Review commit CLI — 原子审查提交链。

单次调用自动执行：审查报告+指标落库 → 兼容投影写入 → 运行日志 → 最终报告。
外部无需再分别调用 review-pipeline / update-state / run-log / user-report，物理杜绝漏跑。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio

from data_modules.config import DataModulesConfig
from data_modules.index_manager import IndexManager
from data_modules.user_report import build_user_report, format_user_report
from data_modules.run_logger import write_run_log

from review_pipeline import _build_review_metrics_record, build_review_artifacts, write_review_report


def _die(stage: str, errors: list[str]) -> None:
    print(json.dumps({"blocked": True, "stage": stage, "errors": errors}, ensure_ascii=False, indent=2), file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Review commit CLI（原子审查提交链）")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--review-results", required=True, help="reviewer 原始结果 JSON")
    parser.add_argument("--metrics-out", default="", help="metrics 输出文件")
    parser.add_argument("--report-file", default="", help="审查报告路径")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    chapter = args.chapter

    # ── 1. 审查报告 + 指标落库（review-pipeline） ──
    try:
        artifacts = build_review_artifacts(
            project_root=project_root,
            chapter=chapter,
            review_results_path=Path(args.review_results),
            report_file=args.report_file,
        )
    except Exception as exc:
        _die("review-pipeline", [f"审查数据处理失败: {exc}"])

    # 输出 metrics JSON
    if args.metrics_out:
        out_path = Path(args.metrics_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(artifacts["metrics"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 生成报告文件
    if args.report_file:
        write_review_report(
            project_root=project_root,
            report_file=args.report_file,
            payload=artifacts,
        )

    # 落库
    try:
        config = DataModulesConfig.from_project_root(project_root)
        manager = IndexManager(config)
        manager.save_review_metrics(_build_review_metrics_record(artifacts["metrics"]))
    except Exception as exc:
        print(f"⚠️  审查指标落库失败（非致命）: {exc}", file=sys.stderr)

    # ── 2. 兼容投影写入（update-state --add-review） ──
    try:
        import subprocess
        from pathlib import Path as _Path
        scripts_dir = _Path(__file__).resolve().parent
        report_file_arg = args.report_file or f"审查报告/第{chapter}章审查报告.md"
        subprocess.run(
            [
                sys.executable, "-X", "utf8",
                str(scripts_dir / "update_state.py"),
                "--project-root", str(project_root),
                "--add-review", f"{chapter}-{chapter}", report_file_arg,
            ],
            check=True, capture_output=True, text=True,
        )
    except Exception as exc:
        print(f"⚠️  兼容投影写入失败（非致命）: {exc}", file=sys.stderr)

    # ── 3. 运行日志 ──
    try:
        write_run_log(
            project_root,
            event="review_commit",
            payload={
                "chapter": chapter,
                "blocking_count": artifacts["review_result"].get("blocking_count", 0),
                "issues_count": artifacts["review_result"].get("issues_count", 0),
                "anti_patterns_added": artifacts.get("anti_patterns_added", 0),
            },
        )
    except Exception as exc:
        print(f"⚠️  运行日志写入失败（非致命）: {exc}", file=sys.stderr)

    # ── 4. 最终报告（user_report） ──
    report_text = ""
    try:
        report = build_user_report(project_root, stage="review", chapter=chapter)
        report_text = format_user_report(report, "text")
    except Exception as exc:
        print(f"⚠️  最终报告生成失败（非致命）: {exc}", file=sys.stderr)

    print(json.dumps({
        "chapter": chapter,
        "review_result": artifacts["review_result"],
        "metrics": artifacts["metrics"],
        "anti_patterns_added": artifacts.get("anti_patterns_added", 0),
        "_user_report": report_text,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.platform == "win32":
        enable_windows_utf8_stdio()
    main()

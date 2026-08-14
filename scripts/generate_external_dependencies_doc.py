#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 capability-requirements.yaml 生成人类可读依赖文档（Markdown）。

用法:
    python scripts/generate_external_dependencies_doc.py
        # 读取 config/environment/capability-requirements.yaml，输出到 stdout
    python scripts/generate_external_dependencies_doc.py --input <yaml> --output <md>
        # 指定输入/输出文件

依赖: PyYAML（项目 .venv 已有 pyyaml）。若缺失则报错并提示安装。
其余仅用标准库。
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

CATEGORY_TITLES = {
    "toolchains": "工具链（Toolchains）",
    "runtimes": "运行时（Runtimes）",
    "engines": "引擎（Engines）",
    "models": "模型（Models）",
    "plugins": "插件（Plugins）",
}

REQUIRED_BY_LABELS = {
    "core-runtime": "核心运行时",
    "ci": "CI",
    "tests": "测试",
    "desktop-build": "桌面构建",
    "desktop-runtime": "桌面运行时",
    "browser-smoke": "browser-smoke",
    "e2e": "e2e",
    "ocr-pipeline": "OCR 管线",
    "asr-pipeline": "ASR 管线",
    "conversion": "格式转换",
    "media-pipeline": "媒体管线",
    "bakeoff": "bake-off",
    "file-detection": "文件检测",
    "workspace-ui": "工作区 UI",
}


def load_yaml(path: str) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - 依赖缺失路径
        sys.stderr.write(
            "错误: 需要 PyYAML。请在项目环境安装: uv add --dev pyyaml 或 pip install pyyaml\n"
        )
        raise SystemExit(2) from exc
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "capabilities" not in data:
        sys.stderr.write(f"错误: {path} 不是合法的 capability-requirements 文件\n")
        raise SystemExit(2)
    return data


def render(data: dict) -> str:
    lines: list[str] = []
    lines.append("# ArcheAxis Knowledge — 外置能力需求清单（机器可读生成）")
    lines.append("")
    lines.append(f"> 本文档由 `scripts/generate_external_dependencies_doc.py` 从机器可读清单生成。")
    lines.append(f"> 机器可读源：`config/environment/capability-requirements.yaml`（schema v{data.get('schema_version', '?')}）")
    lines.append(f"> 更新日期：{data.get('updated', '?')} | 权威人类文档：`{data.get('source_of_truth', '?')}`")
    lines.append(f"> 说明：{data.get('description', '')}")
    lines.append("")

    for category, title in CATEGORY_TITLES.items():
        items = data["capabilities"].get(category, [])
        lines.append(f"## {title}（{len(items)} 项）")
        lines.append("")
        lines.append("| 名称 | 用途 | 版本范围 | 平台 | 许可 | 安装方式 | 本机限定 | 健康检查 | 依赖方 |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for item in items:
            required_by = "、".join(
                REQUIRED_BY_LABELS.get(rb, rb) for rb in item.get("required_by", [])
            )
            local_only = "是" if item.get("local_only") else "否"
            lines.append(
                "| {name} | {purpose} | `{ver}` | {platform} | {license} | {method} | {local} | `{hc}` | {rb} |".format(
                    name=item["name"],
                    purpose=item.get("purpose", ""),
                    ver=item.get("version_range", ""),
                    platform=item.get("platform", ""),
                    license=item.get("license", ""),
                    method=item.get("install_method", ""),
                    local=local_only,
                    hc=item.get("healthcheck_command", ""),
                    rb=required_by,
                )
            )
        lines.append("")
        lines.append("### 来源")
        lines.append("")
        for item in items:
            lines.append(f"- **{item['name']}**：{item.get('source_url', '')}")
        lines.append("")
    lines.append("---")
    lines.append(f"_生成时间：{date.today().isoformat()}（本地）_")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="从 capability-requirements.yaml 生成人类可读 Markdown 依赖文档"
    )
    parser.add_argument(
        "--input",
        default="config/environment/capability-requirements.yaml",
        help="机器可读需求清单路径（默认 config/environment/capability-requirements.yaml）",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出 Markdown 路径；缺省输出到 stdout",
    )
    args = parser.parse_args()

    data = load_yaml(args.input)
    doc = render(data)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(doc)
        print(f"已生成: {args.output}")
    else:
        sys.stdout.write(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

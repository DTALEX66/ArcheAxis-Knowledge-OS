# AXW-096A 性能基准：首轮真实数据（2026-08-14）

> 状态：**PASS（首轮基线）**。分层语料 = 公开领域 Project Gutenberg 英文书
> （5 本，sources.json 记录来源/许可/获取时间/SHA，见 `.hermes/task-runtime/corpus/`）。
> 真实大库与 H4-EXIT 验收仍留 Owner；本记录是 096A 的**数据采集层**证据。

## 硬件

| 项 | 值 |
|---|---|
| 平台 | Windows 11 (AMD64) |
| CPU | 20 核 |
| Python | 3.12.13 |

## 语料分层（公开领域，Project Gutenberg）

| 层 | 文件 | 大小 |
|---|---|---|
| small | 1 本 | 147.6 KiB |
| medium | 4 本 | 1,873.4 KiB |
| large | 5 本（+分层副本） | 4,759,539 B / 4.5 MiB |

来源：gutenberg.org（id 84/1342/11/1661/98），许可 public-domain，逐样本
sha256 已记录于 `corpus/sources.json`。

## 测量（CPU-only，无 GPU）

| 层 | 转换中位延迟 | 转换 p95 | 内存峰值 |
|---|---|---|---|
| small | 2.649 ms | — | 1.162 MiB |
| medium | 8.244 ms | — | 1.727 MiB |
| large | 10.418 ms | — | 1.762 MiB |

- 冷启动（全新解释器 import core）：**52.751 ms 中位**（3 样本）
- 转换链路：`convert_directory_resumable`（真实管线，非占位）
- 内存：tracemalloc 峰值

## 降级阈值裁决

| 阈值 | 限制 | 实测 | 裁决 |
|---|---|---|---|
| import-latency | 5000 ms | 52.751 ms | ✅ passed |
| memory | 2048 MiB | 1.762 MiB | ✅ passed |

**overall: passed** —— 完整 JSON 报告：
`.hermes/task-runtime/benchmark/benchmark.json`（不入库）

## 复现

```bash
python scripts/prepare_benchmark_corpus.py --proxy 127.0.0.1:7890   # 分层语料
python scripts/run_performance_benchmark.py                          # 测量 + 报告
```

注：语料正文不提交仓库（公开语料可再获取）；本记录只含指标与来源元数据。

# AXW-096A 性能基准：首轮真实数据（2026-08-14）

> 状态：**PASS（首轮基线）**。分层语料 = 公开领域 Project Gutenberg 英文书
> 10 本 + 中文经典 4 本（sources.json 记录来源/许可/获取时间/SHA，见
> `.hermes/task-runtime/corpus/`）。
> 真实大库与 H4-EXIT 验收仍留 Owner；本记录是 096A 的**数据采集层**证据。

## 硬件

| 项 | 值 |
|---|---|
| 平台 | Windows 11 (AMD64) |
| CPU | 20 核 |
| Python | 3.12.13 |

## 语料分层（公开领域，Project Gutenberg）

| 层 | 组成 | 文件 | 大小 |
|---|---|---|---|
| small | 1 英文 + 1 中文 | 2 txt | 2,415,262 B / 2.3 MiB |
| medium | 4 英文 + 2 中文（+分层副本） | 7 txt | 6,074,578 B / 5.8 MiB |
| large | 10 英文 + 4 中文 | 14 txt | 13,058,571 B / 12.5 MiB |

来源：gutenberg.org（en id 84/1342/11/1661/98/2701/1400/74/76/43；
zh id 23962 西遊記/24264 紅樓夢/24032 儒林外史/24141 警世通言），
许可 public-domain，逐样本 sha256 已记录于 `corpus/sources.json`。

## 测量（CPU-only，无 GPU，中英文混合语料）

| 层 | 组成 | 转换中位延迟 | 内存峰值 |
|---|---|---|---|
| small | 1 英文 + 1 中文 | 6.958 ms | 2.021 MiB |
| medium | 4 英文 + 2 中文 | 17.061 ms | 2.028 MiB |
| large | 10 英文 + 4 中文 | 35.089 ms | 2.037 MiB |

- 冷启动（全新解释器 import core）：**53.236 ms 中位**（3 样本）
- 转换链路：`convert_directory_resumable`（真实管线，非占位；中文经典小说
  西遊記/紅樓夢/儒林外史/警世通言，公共领域）
- 内存：tracemalloc 峰值
- 规模-延迟关系近似线性（2.3→12.5 MiB 语料，延迟 7→35 ms），内存随规模
  基本稳定（~2 MiB），无退化

## 降级阈值裁决

| 阈值 | 限制 | 实测 | 裁决 |
|---|---|---|---|
| import-latency | 5000 ms | 53.236 ms | ✅ passed |
| memory | 2048 MiB | 2.037 MiB | ✅ passed |

**overall: passed** —— 完整 JSON 报告：
`.hermes/task-runtime/benchmark/benchmark.json`（不入库）

## 复现

```bash
python scripts/prepare_benchmark_corpus.py --proxy 127.0.0.1:7890   # 分层语料
python scripts/run_performance_benchmark.py                          # 测量 + 报告
```

注：语料正文不提交仓库（公开语料可再获取）；本记录只含指标与来源元数据。

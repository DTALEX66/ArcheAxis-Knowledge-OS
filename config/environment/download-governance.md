# 能力资产下载治理规则（Download Governance）

> 适用：外置能力仓（`OS External Configuration`）中所有**下载类资产**的管理，
> 配套工具：`scripts/capability_download.py`。
> 目标分区语义：`60-cache/downloads`（暂存）、`90-quarantine/`（隔离）、
> `40-models/`（模型激活目标）、`00-registry/licenses/`（许可归档）。

## 0. 核心原则

1. **禁止静默首次下载**：任何工具/脚本不得在用户不知情时自动下载资产。
   首次获取必须显式 `stage`，打印来源、体积、许可证、磁盘位置。
2. **三段式生命周期**：`stage`（暂存）→ `verify`（sha256 校验）→ `activate`（原子激活）。
3. **许可证门槛**：许可证未知（`unknown`）或缺失的资产**不得激活**（`activate` 拒绝，
   除非 `--force` 显式放行——放行行为必须在日志中留痕）。
4. **原子激活**：激活先写入同盘临时文件，校验通过后 `os.replace` 到目标，杜绝半成品。
5. **隔离区**：哈希不符、来源可疑、被拒绝的资产一律 `quarantine` 到 `90-quarantine/`，
   隔离后不再被任何 verify/activate 引用。

## 1. 命令语义

```bash
# 1) 暂存（默认不激活；dest-dir 使用 60-cache/downloads 语义）
python scripts/capability_download.py stage <url> --dest-dir <staging> \
    --license <SPDX> [--license-url <url>] [--name <name>]

# 2) 校验（重算 sha256 与 manifest 对比；不一致退出码 1）
python scripts/capability_download.py verify <manifest.json>

# 3) 激活（hash + license 校验通过后原子放入 store-root，如 40-models/）
python scripts/capability_download.py activate <manifest.json> <store-root>

# 4) 隔离（默认移入 90-quarantine/<时间戳>/，相邻 manifest 一并隔离）
python scripts/capability_download.py quarantine <path>
```

- `stage` 若目标文件已存在：**拒绝覆盖**（需 `--force` 显式声明）。
- `activate` 若 store-root 中已存在同名资产：**拒绝覆盖**（需 `--force`）。
- 支持的 URL scheme：`http` / `https` / `file`（本地测试）。

## 2. Manifest 结构

`<name>.download-manifest.json`（与暂存文件同目录）：

```json
{
  "manifest_version": 1,
  "tool": "capability_download",
  "name": "...",
  "source_url": "https://...",
  "sha256": "...",
  "size_bytes": 123,
  "license": "MIT",
  "license_url": "https://...",
  "downloaded_at": "ISO-8601",
  "staged_file": "<name>",
  "staging_dir": "<绝对路径>"
}
```

## 3. 用户授权

- **人工下载授权**：首次 stage 视为一次显式授权；`--dest-dir` 必须显式给出，
  工具无任何“默认目录自动下载”路径。
- **自动流程授权**：CI / 编排脚本若需自动获取资产，必须先在此文档登记
  目标 URL、用途、许可证，并限定 `--dest-dir` 为 `60-cache/downloads`；
  未经登记的工具链不得自动 stage。
- 许可证原文归档到 `00-registry/licenses/<name>-LICENSE`（`--license-url` 指向官方来源）。

## 4. 可疑资产处置

| 情形 | 处置 |
|---|---|
| `verify` 哈希不一致 | 立即 `quarantine`，重新 stage；排查来源是否被替换 |
| 许可证缺失/unknown 且无授权 | `activate` 拒绝；补登记许可证或 `quarantine` |
| 来源域名不在登记清单 | `quarantine`，人工复核后才可重新 stage |
| 激活后运行期异常 | 资产移回暂存区复核，必要时 `quarantine` |

## 5. 与 00-registry 的关系

- `activate` 成功后，资产 sha256/许可证登记进 `00-registry/model-lock.json`（R2 规划）。
- 每次 `quarantine` 应在审计日志（`logs/environment-audit/`）留痕：来源、时间、原因。

## 6. 禁止事项

- 禁止 `curl -o` / `Invoke-WebRequest` 等裸下载命令直接写入能力仓分区（绕过治理）。
- 禁止删除隔离区资产而不留审计记录。
- 禁止修改已激活资产的哈希或绕过 `verify` 直接使用暂存文件。

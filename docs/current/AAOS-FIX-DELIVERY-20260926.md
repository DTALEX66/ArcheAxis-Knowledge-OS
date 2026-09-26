# AAOS 修复交付与遗留清单（2026-09-26）

- 分支：`codex/aaos-p3-ui-convergence-20260922`
- 交付 HEAD：`e8e6909d68d4dd1655cf06905a22a1ca5fa458ba`（已推送，本地=远端）
- 前置提交：`caf4ab3c`（能力清单协议化修复）
- 证据等级：`EXACT_SHA_CI`（`e8e6909d` 全绿）+ `TESTED_LOCAL`（3335 passed）

## 1. 已交付

| # | 提交 | 内容 | 证据 |
| --- | --- | --- | --- |
| 1 | `caf4ab3c` | `install_builtin` 改以 `to_dict()` 协议判别，不再用 `isinstance` | RED→GREEN 已复现；105 passed |
| 2 | `caf4ab3c` | `AAOS-UI-SUITE-COVERAGE-20260923.md:4` 尾随空格（CI `lint` 拦截点） | CI `lint` 由 failure→success |
| 3 | `e8e6909d` | 43 个 doc/authority/state 文件（既存未提交工作集） | 全套 15 failed→4 failed |

### CI 结果（exact SHA）

| 运行 | SHA | 结论 | 作业 |
| --- | --- | --- | --- |
| [36230328734](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36230328734) | `edf9a7e5` | **failure** | `lint` ✗、`a0-gates` ✗ |
| [36233364335](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36233364335) | `caf4ab3c` | **failure** | `lint` ✓、`test (3.12)` ✗ 15 failed |
| [36233950853](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36233950853) | `e8e6909d` | **success** | `gateplan` ✓、`lint` ✓、`a0-gates` ✓ |

> `e8e6909d` 的 `test` 作业被 gateplan 按改动路径判为可跳过（仅文档改动）。这是**选择性 SKIP**，已核对 diff 确实只含文档，属正确跳过。

## 2. `install_builtin` 缺陷的根因与证明

CI nightly 报：

```
ValueError: plugin manifest: PluginManifest(...) is not of type 'object'
app/capability/store.py:268: in install_builtin
    else load_manifest_from_mapping(manifest)
shared/plugin_manifest.py:391: in load_manifest_from_mapping
shared/plugin_manifest.py:212: in validate
```

**根因**：`install_builtin` 用 `isinstance(manifest, PluginManifest)` 判断清单是否已解析。当清单来自**同一模块的第二次导入**（重复检出、被安装副本遮蔽源码树、打包运行时）时，它是同一契约下**不同的类对象**，`isinstance` 返回 `False`，于是合法的 `PluginManifest` 被回退送进 `load_manifest_from_mapping()`，再由 jsonschema 以"不是 object"拒绝。

**证明（RED→GREEN）**：新增 `tests/test_axw_cap503_builtin.py::test_store_accepts_manifest_from_a_second_module_identity`，用 `importlib` 以第二个模块名重载 `shared/plugin_manifest.py` 来**确定性复现**该身份分裂：

- 对旧代码：失败于 `store.py:268 → plugin_manifest.py:391 → :212`，报文与 CI **逐字节一致** → 复现成立
- 对新代码：通过

**修复**：以 `callable(getattr(manifest, "to_dict", None))` 判别协议，而非类身份。`PluginManifest` 的 `to_dict()` 是契约上真正的判别特征。行为保持 fail-closed（字符串/字典仍走解析，非法输入仍被拒）。

## 3. 为什么 CI 会在 `main` 上连续 6 天红

两个独立原因叠加，且都不在外部审计报告的诊断范围内：

1. **门禁未运行过**：`main` 上最近的 CI 运行都是文档改动，gateplan 只跑 `lint`，**`test` 作业一直被 SKIP**；`lint` 又在 2026-09-23 被一个尾随空格卡住。真正跑全套的只有 `nightly` cron。
2. **契约与文档不一致**：仓库中**已提交的契约测试已经要求**新的文档内容，但那些文档更新**从未提交**，只存在于工作区。因此任何一次真实全套运行都会因读取到旧文档而失败。

nightly 在 `main` 的失败：2026-09-21 至 09-26 连续 6 次，失败作业 `full-suite`（`py-compat` 通过）。

## 4. 遗留失败（4 项，均已定位，未修复）

以下在提交 `e8e6909d` 后仍然失败。**均不是本次改动引入**（`git show --stat` 可证）：

| 测试 | 现象 | 分类 | 可本地复现 |
| --- | --- | --- | --- |
| `test_axr060_completion_audit.py::test_tracked_current_surfaces_only_reference_declared_release_delta_or_source_objects` | `docs/current/` 某 40 位 SHA 既不在白名单、也不是可达 commit 或 tree | **仅 CI**：`a9aa0665` 提交对象存在于本地与 GitHub，但其分支 `chore/naming-repo-refs` 已删除，CI 检出后不可达 | 否（本地对象库仍有该对象，故通过） |
| `test_project_output_routing_contract.py::test_formal_desktop_window_is_the_archeaxis_workspace_shell` | 断言 `'content_base64' in <C# 源码>` 失败 | 契约与实现不一致 | 是 |
| `integration-tests/test_axw_main_chain_e2e.py::test_axw_main_chain_full_e2e[html]` | `conversion engine outside the real chain`：`'html-adapter' in {'safe-http+raw','trafilatura'}` | 契约与实现不一致 | 是 |
| `integration-tests/test_axw_main_chain_e2e.py::test_axw_main_chain_docx_when_markitdown_available` | 同上族 | 契约与实现不一致 | 是（本次仅复现 html 参数化） |

### `a9aa0665` 说明（需要 Owner 决策）

- 该提交（2026-08-12，`ci(naming): scope restore-keys under -naming-v2`）在 GitHub 上**仍可读取**，但其分支已删除，因此在 `main` 的检出中不可达。
- 它被**已提交的** `docs/current/BRANCH-CONVERGENCE.json` 与 `docs/current/R5-BRANCH-DISPOSITION-20260918.md` 引用。
- 三种处置方式，**都需要 Owner 判定**，因为它们改变证据语义：
  1. 恢复分支引用使提交可达（最小改动，但会复活一个已判定 `DELETE_CANDIDATE` 的分支）；
  2. 更新这两份审计文件，把"已删除分支的 tip"标注为非当前可达证据；
  3. 放宽该测试的语义（**不建议**：它会削弱"只引用真实对象"的安全护栏）。

## 5. 已执行的安全清理

`git gc`（默认 prune 期限，保守）：

| 指标 | 前 | 后 |
| --- | --- | --- |
| `garbage` | **5**（`tmp_pack_*`） | **0** |
| `size-garbage` | 8.95 MiB | 0 |
| 松散对象 | 13 | 0 |
| `in-pack` | 27309 | 27044 |
| `size-pack` | 447.59 MiB | 447.31 MiB |

- **99 个引用完全未变**（逐条比对 `refs-before-gc.txt`）→ `refs/codex/**` 42 条完好
- 受保护巨型 blob（`aab1ec6f…` 154 MB）仍然存在，**证明引用保护生效**
- 提交 `caf4ab3c` 对象完好

清理**不会**缩小 447 MiB 主体：体积来自 `refs/codex/turn-diffs/checkpoints/**` 引用的检查点快照（**Codex CLI 自有状态**，`AGENTS.md` §3 禁止越权处置）。
## 6. 明确驳回的外部审计处方

| 处方 | 驳回理由 |
| --- | --- |
| `git for-each-ref … \| grep -v master \| xargs -P4 -n1 git branch -D` | 干跑证明会命中**全部 27 个本地分支**（含 `main` 与当前分支），因过滤器写 `master` 而本仓库默认分支是 `main` |
| `git-filter-repo --sensitive-data-removal` | 无敏感泄露证据；会重写全部 99 个引用（含 Codex 检查点）并需 force push |
| `fast_mode=true` / `shell_snapshot=true` | 该 Codex CLI 中**不存在**这两个配置键 |
| `preferred_auth_method` / `web_search=false` | `config.toml` 中**不存在**这两个键 |
| 安装 `@softspark/dsh-codex@1.4.0` | 该版本面向 DSH `0.1.1-rc.2`，本机 host 为 `0.1.5-rc.2`（registry latest 已 1.6.2） |
| `reflog expire --expire-unreachable=now` 作为回滚手段 | 方向相反：它会**清除**恢复信息 |
| SSH/HTTPS 排查（标为高优先级） | `ssh -T` 已成功认证、`credential.helper=manager`、URL 改写均已就位——零工作量 |

详见 `docs/current/AAOS-EXTERNAL-AUDIT-VERIFICATION-20260926.md`（含附录 A）。

## 7. 未验证边界

- `e8e6909d` 的 **`test` 作业被跳过**，未在该 SHA 上取得精确全套 CI 结论。本地同工作树结果为 3335 passed / 4 failed。
- `nightly` 的下一次 cron 是验证 4 项遗留失败是否消除的唯一精确 CI 途径。
- `macos`/`windows` 运行时作业、桌面构建、安装器生命周期在本轮均为 SKIP，未验证。
- `shared/provider_routing.py` 存在仅行尾/空白漂移（`git diff --numstat` 为空），**故意未提交**。

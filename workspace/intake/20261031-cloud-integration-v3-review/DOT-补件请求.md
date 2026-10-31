# 给 GPT 云端 DOT 的补件提示词

请对你交付的 `AAOS-Cloud-Integration-20261031-v3.zip` 做一次补件和定向核查，不重做已经可靠验证且未变化的全量实验。

原包 SHA-256：`de984bf8917d24f4bc837221f76983dde20973f8285808e1fa6c351a5c68ac43`；云端基线：`8d367bac4a85bebfbb523503678ade0838faa73e`。

本地 Codex 已核验 1,874 个成员和内部 1,873 项清单；主要 Python/Rust/jsdom 测试数量有原始日志支持。现在只请处理以下缺口：

1. 补交生成映射时使用的原始 `05-format-results-template.csv`、`06-interop-results-template.csv`。请提供原字节文件、SHA-256、原路径及22/37行计数，并说明与 `deliverable/mappings/input-inventory-hashes.json` 的登记是否一致。不要用最终映射反向生成原模板。
2. 核对命令索引引用但 ZIP 未包含的 `logs/full/final-freeze.stdout`、`logs/wheel-smoke/export.stdout`。有原文件就原样补交；若原本为空、从未生成或已丢失，如实说明并纠正索引。重新运行产生的输出必须另起名称和日期，不能冒充当时日志。
3. 核查检测器实际加载的模型/config与回执 `model_sha256` 的绑定。静态审计发现：`worker_detect.detect` 仍从 caller `repo_root` 取模型计算hash，实际 `shared.file_detection` 可使用安装目录或 `ARCHEAXIS_MAGIKA_MODEL_DIR`；现有恶意root测试复制相同模型，未覆盖不同字节。请给出判断依据；如确认不一致，仅提供最小候选修复和相关定向反例，保持权限、版本及receipt校验，不重跑无关全套。
4. 修正复现脚本的证据保全和前置失败处理：`harness/full_suite_reproduce.sh:13–15` 会覆盖原 `deliverable/config/full-ci-locked.txt`，失败后可能继续使用旧文件；venv创建和旧环境复用也须明确。新输出应落独立run，必要前置失败须停止依赖步骤，原交付证据不改写。说明 `--system-site-packages` 对干净复现的限制。
5. 明确主补丁已包含 detector、资源重绑和安全锁三份子候选，不能重复叠加。本地已前进到 `70dfc397`，只读检查有13路径不适用；不要要求直接覆盖本地源码，也不要把云端旧PASS移绑为本地当前PASS。无需获取或上传本地源码来完成本次补件。

保留原 v3 不变，另交 `v3.1-supplement.zip`，包含补交原件、必要最小补丁、定向验证的实际命令/退出码/stdout/stderr、成员SHA清单，以及“补齐/修复/仍缺失”逐项答复。只需打包新增和变更内容，并以原包SHA绑定，不再复制全部历史日志、数据库和构建产物。

没有的文件、无法验证的结论明确标 `MISSING` 或 `UNVERIFIED`。不伪造历史日志，不把静态映射、jsdom、Linux或故障观测通过当作Windows原生/H5P/真实模型/完整产品验收。仅在原隔离副本中处理，不推送、发布，不改正式仓库、其他项目、真实资料、账号或全局配置。

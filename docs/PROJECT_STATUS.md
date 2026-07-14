# 项目当前状态

> 更新：2026-07-14。本页是当前状态入口；旧审计文件是历史快照。

## 已验证能力

- Core `/run` 的 route/execute/trace/evaluate 存储链可运行；Planner 仍以固定 echo 步骤为主，不能视为真实动态认知闭环。
- Runtime、Knowledge、Research、Enhancement、Contracts 五个 Facade 已有真实 tracer bullet；Phase 1 的 Contracts 起点是 identity re-export，不代表全量版本化 Schema。
- Phase 2 已建立 `TaskPackV1`、`ExecutionTraceV1`、`EvaluationV1` 与 `LessonV1`：TaskPack 支持 KB dataclass/SQLite row 无损往返、Runtime 窄投影和可回滚迁移；Execution Trace 与 Lesson 支持 Runtime/SQLite row 无损往返并对未知行字段 fail closed；Evaluation 支持 Runtime 无损往返。
- Research 已迁为可安装的 `inspiration_research` 包；旧连字符目录只保留 deprecated source-checkout launcher。
- Architecture Guard 在 CI 阻止新增路径注入、反向依赖和外部绝对路径硬编码。
- Core 与 Knowledge-Base 使用单端口挂载。
- Ruff 覆盖 `app shared knowledge_base inspiration_research Inspiration-Research` 及集成适配器和脚本。
- OS 与 KB 使用分离测试套件，避免包名和 sleep-loop 状态账本互相干扰。
- `/health` 实时递归统计 HTTP 操作，不再维护手写端点数字。
- 数据库通用表名、排序字段经过标识符/Schema 校验。
- `/kb/export` 只允许明确的知识表白名单。
- `auth.enabled` 已接入中间件；生产模式拒绝关闭鉴权、通配 CORS 或缺少 API Key。
- n8n、Airflow、LiteLLM 和 crawler 适配器不再返回 stub 假成功。
- Obsidian 外部路径必须显式传入，API 不再默认访问个人 E 盘。
- 外部 A 项目（Obsidian-Assistance）的分析与通用能力吸收已结束；后续严格只读且不再扫描或作为迁移目标。

## 质量能力

- `shared/processing_manifest.py`：文件级 JSONL、源/输出 SHA-256 和指纹校验恢复。
- `app/ingestion/multi_format.py::convert_directory_resumable()`：原子落盘 Markdown、失败重试、变更重跑。
- `shared/accuracy_benchmark.py`：人工真值 CER/WER；无样本明确 `unverified`。
- `shared/evidence_verification.py`：文本命中证据；所有调用者提供的内容最高为候选，当前没有服务端可信 provenance，必须人工复核。
- `shared/content_quality.py`：乱码、水印、误导性 100% 和 Wikilink 静态审计。
- `shared/oer_crosswalk.py`：静态开放来源发现建议（遗留文件名），不检索内容、不检查许可、不做 claim-level crosswalk。

## 仍保留的债务

1. `knowledge_base/api.py` 仍包含遗留领域路由；复合、质量、投影路由已经拆出，后续继续按领域迁移。
2. `knowledge_base` 与 `inspiration_research` 均可安装；`Inspiration-Research` 只保留 launcher 兼容，不再保存第二份业务实现。
3. 旧细粒度 API 仍公开，路由面尚未真正缩减。
4. 生产部署尚缺独立容器/反向代理/并发负载验证。
5. OCR/ASR 的真实准确率取决于用户提供人工标注金标准，代码不能代替人工真值。
6. Mypy 尚未作为零错误门禁；当前历史模块仍有返回类型、异构字典和可选导入类型债务。
7. Dynamic Planner、多维 Evaluation、Lesson 反馈和统一 Runtime/Sleep Loop 仍属于后续路线图，而非当前完成能力。

## 正式门禁

```bash
python -m pytest tests -q --tb=short
cd knowledge_base && python -m pytest tests -q --tb=short
python -m pytest integration-tests -q --tb=short
python -m ruff check app shared knowledge_base inspiration_research Inspiration-Research shared-contracts/adapters app/workflow integration-tests scripts
```

最终交付时以这些命令的真实输出为准，不以本页手写数字证明完成。

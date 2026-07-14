# Phase 0 安全基线

> Git 基线：`82b9df3f719d9212111536b454654f2243150f16`。范围仅限当前仓库 HEAD；证据包括静态代码审计和本次真实门禁，不等同于渗透测试、Git 历史扫描或部署验收。

## 执行摘要

生产配置具备鉴权必须开启、密钥必须显式提供、CORS 禁止通配符的 fail-fast 基线；SQLite 备份使用 online backup，并在恢复前验证候选快照。当前三个 P0 安全边界仍未闭合：

1. 已认证身份缺少端点级 RBAC，`readonly`、`user` 与 `admin` 没有写操作隔离。
2. 用户可控 URL 缺少完整 SSRF 防护，未统一拒绝回环、私网、链路本地、重定向后地址和超大响应。
3. 部分 API 绕过已有路径 containment，可读取、扫描或写入 approved root 之外的本地路径。

## 高置信秘密扫描

- 状态：**passed**
- 匹配数：0
- 规则：私钥头、GitHub token、OpenAI 风格 key、AWS access key。
- 范围：HEAD 中的 Git 跟踪文件；未扫描 Git 历史，不等同于 gitleaks/detect-secrets。
- 测试占位符和已知开发默认值不被误报为真实生产凭据；报告不得复述任何 credential 值。

## 已实现事实

| 控制域 | 仓库内证据 | 结论 |
|---|---|---|
| 共享鉴权 | `shared/auth.py:174-218`; `app/main.py:46-100`; `knowledge_base/api.py:43-78`; `Inspiration-Research/api.py:35-69` | 三个 FastAPI 应用共享 API key/Bearer 鉴权；公开路径有显式白名单。 |
| Token | `shared/auth.py:103-160`; `app/main.py:333-353` | HMAC-SHA256 token 校验签名与过期时间；token 签发显式要求管理员角色。 |
| 生产 fail-fast | `shared/config.py:177-243`; `docker-compose.yml:8-18,42-52` | 生产拒绝关闭鉴权、弱/缺失 secret、固定开发 key 与通配 CORS。 |
| CORS | `shared/config.py:126-175,213-229` | 生产 origins、methods、headers 均经过约束，默认不允许 credentials。 |
| 安全摄入 | `app/ingestion/file.py:8-51,68-112`; `knowledge_base/routers/quality.py:34-54` | 常规文件摄入与质量目录对仓库根执行 resolve + containment，并限制扩展名和规模。 |
| SQLite/备份 | `app/memory/database.py:19-26`; `shared/storage.py:282-450`; `shared/backup.py:24-91`; `tests/test_backup.py` | 关键 CRUD 使用参数绑定/allowlist；备份使用 SQLite online backup；恢复只生成并校验离线候选。 |
| 部署 | `Dockerfile:28-39`; `.github/workflows/ci.yml` | 容器以非 root 用户运行；现有单元、KB、集成及部署测试可阻断 CI。 |

## P0 缺口

| ID | 事实与影响 | 证据 | Phase 1/3 验收方向 |
|---|---|---|---|
| SEC-P0-01 | **端点级 RBAC 未系统化。** `/auth/token` 已要求 admin，但写入、导入、执行、备份等其他敏感端点未按角色拒绝；认证不等于授权。 | `app/main.py:333-361`; `shared/auth.py`; `knowledge_base/api.py:136-177` | 为敏感路由声明 admin/operator 权限；`readonly` 对所有变更操作稳定返回 403，并补合同测试。 |
| SEC-P0-02 | **SSRF 面。** `/convert/url`、KB pipeline、feed、n8n/Airflow 接受用户影响的 URL，只做 scheme 检查或完全不检查；未防私网、metadata、DNS rebinding、重定向和响应体放大。 | `app/main.py:296-314`; `app/ingestion/multi_format.py:187-211`; `knowledge_base/routers/composite.py:24-34`; `shared/pipeline.py:60-83`; `shared/feed_collector.py:105-118`; `app/workflow/n8n.py:13-16` | 建立 `safe_http_fetch()`：逐跳解析/校验 DNS 与 IP、限制端口/重定向/超时/响应大小；Webhook 使用 allowlist。 |
| SEC-P0-03 | **路径 containment 绕过。** `/convert/file`、`/convert/directory`、KB `/sources`、Obsidian/media 与 projection 路径没有统一允许根目录，可触及任意可读/可写路径。 | `app/main.py:296-362`; `app/ingestion/multi_format.py:152-256`; `knowledge_base/routers/composite.py:143-168`; `shared/source_discovery.py:45-109`; `shared/obsidian_projection.py:180-201` | 输入根与输出根分权；resolve 后验证 containment，并处理 symlink/junction 逃逸。 |
| SEC-P0-04 | 开发默认鉴权关闭且 CORS 为 `*`；若误绑外网，固定开发身份与跨域访问会放大暴露面。 | `shared/config.py:18-55`; `config/settings.yaml:1-14`; `README.md:59-79` | development 默认只绑定 loopback；外网绑定时强制开启鉴权并拒绝 wildcard CORS。 |

## 其他缺口

- JWT/API key 明文存储，未见 `chmod 0600` 或 Windows ACL、key ID、轮换、撤销、`aud`/`iss`；`token_expire_hours` 尚未接入签发路径（`shared/auth.py:82-103`; `shared/config.py:45-49`）。
- `shared/rate_limit.py` 未接鉴权失败和 token 签发；没有锁定策略。
- 未见 Trusted Host、HTTPS redirect 或 HSTS；需由应用或反向代理明确承担。
- 多处 HTTP 客户端整页读取，Crawl4AI 调用缺少显式总超时与响应大小上限。
- `shared.storage` 未统一启用 `foreign_keys`、`busy_timeout`、`synchronous`；多个直接 `sqlite3.connect()` 入口导致 PRAGMA 漂移。
- DB、备份与恢复候选未加密或显式加固 ACL；没有异地副本、调度告警、RPO/RTO 与恢复演练。
- `/backups` 可返回绝对路径，且备份相关端点没有管理员授权。
- 工具参数与结果可原样持久化到 SQLite，缺少集中 secret redaction 和敏感字段白名单（`app/memory/database.py:367-380`）。
- CI 缺少 CodeQL/SAST、依赖审计、Git 历史 secret scan、SBOM、容器扫描和最小 `permissions:`；Actions 未固定完整 SHA，依赖和基础镜像无锁定摘要。

## 生成器控制摘要

| ID | 状态 | 证据 | 结论 |
|---|---|---|---|
| SEC-01 | implemented + tested | `shared/config.py`; `tests/test_hardening.py` | 生产环境对鉴权、强密钥和显式 CORS fail-fast。 |
| SEC-02 | implemented + tested | `shared/auth.py`; `tests/test_hardening.py` | 主网关和独立 KB 共享鉴权；发 token 需要管理员身份。 |
| SEC-03 | implemented + tested | `shared/backup.py`; `tests/test_backup.py` | 恢复只生成离线候选，不在线覆盖活动数据库。 |
| SEC-04 | partial | `app/ingestion/file.py`; `app/ingestion/multi_format.py` | 单文件摄入有仓库 containment；多格式目录需统一 approved roots。 |
| SEC-05 | gap | `app/ingestion/multi_format.py`; `knowledge_base/` collectors | 尚无统一 Safe HTTP Facade 覆盖 DNS、私网、redirect、大小和类型。 |
| SEC-06 | gap | `.github/workflows/ci.yml` | CI 尚未接入高置信 secret scan、依赖审计和架构守卫。 |

## 修复优先级

1. **P0：**端点级 RBAC、统一 SSRF 防护、统一 approved-root containment。
2. **P1：**开发 loopback 强制、集中 SQLite 连接工厂、secret redaction、CI 安全门禁。
3. **P2：**token 生命周期、备份加密/异地副本、恢复演练和供应链可复现。

## 验证限制

- 本报告没有声称渗透测试、Git 历史扫描、真实反向代理、TLS 或容器运行时已通过。
- GitHub Actions 状态必须在推送后独立核对。

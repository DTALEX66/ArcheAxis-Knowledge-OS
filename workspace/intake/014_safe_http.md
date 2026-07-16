# Phase 3 TaskPack：统一 Safe HTTP

> 状态：completed
> 当前刀：统一 URL 消费的安全边界
> Ownership：`shared/safe_http.py`、`tests/test_safe_http.py`、首批调用方 Adapter

## 目标

建立唯一 Safe HTTP Facade，替换用户可影响 URL 的直接网络消费。所有调用方必须经过同一套 DNS、IP、redirect、大小、类型和 timeout 合同。

## 允许范围

- 新增 `shared.safe_http` 标准库实现；
- 新增负向安全合同测试；
- 逐步替换以下直接 URL 消费：
  - `app/ingestion/multi_format.py`；
  - `app/workflow/n8n.py`；
  - `app/workflow/airflow.py`；
  - `shared/feed_collector.py`；
  - `inspiration_research/project_radar/collectors/github_trending.py`；
  - `shared/youtube_extractor.py`；
  - `shared/web_search.py`；
- 增加调用方显式 Content-Type、大小和 webhook allowlist 策略。

## 禁止范围

- 不修改 approved source/output roots；
- 不修改稳定哈希、FTS/Vector rebuild 或数据库 Schema；
- 不引入新的网络依赖；
- `defusedxml` 仅作为远程 XML 的安全解析依赖，不提供网络传输；
- 不访问 `E:`、外部项目或个人 Vault；
- 不把 mock、preview、dry-run 或请求成功冒充内容验证成功；
- 不在同一 TaskPack 顺手重构调用方业务逻辑。

## 安全合同

1. 只允许绝对 `http`/`https` URL；拒绝 credentials、非法端口和不支持 scheme。
2. 每次 DNS 解析的所有结果都必须通过 IP 分类检查；拒绝 loopback、RFC1918、link-local、unspecified、multicast、reserved 和 cloud metadata 地址。
3. 每次 redirect 必须重新解析和复核，禁止 redirect escape。
4. 连接目标必须绑定到已验证的解析结果，不能把已验证 hostname 与后续未验证连接目标分离。
5. connect/read/total timeout 必须有上限并传递到实际请求。
6. response 按字节流式读取，超过上限立即中止。
7. Content-Type 必须由调用方显式 allowlist；不匹配时 fail closed。
8. webhook/工作流 URL 必须使用 allowlist 或显式 operator policy。
9. 网络异常、解析异常、超限和策略拒绝均不得返回 success/stub 结果。

## 首批验收

- 负向测试覆盖私网、回环、link-local、metadata、DNS 混合结果、非法 redirect、超限 response 和错误 Content-Type；
- `n8n`、`Airflow` 不再直接调用 `requests.post`；
- feed、GitHub trending、URL conversion 不再直接调用 `urllib.request.urlopen`；
- YouTube oEmbed/RSS、DuckDuckGo、网页内容提取不再直接打开 URL；
- `youtube-transcript-api` 的内部网络访问保持 deferred，必须在后续 TaskPack 中提供可验证 transport adapter；
- 旧调用方的领域结果结构保持兼容；
- 没有新增硬编码外部路径、凭据或网络依赖；
- 安全任务完成独立 frozen tree、完整本地门禁、reviewer GO 和 exact-SHA CI。

## 回滚

Safe HTTP Facade 切换前保留旧入口，但旧入口不得继续作为默认网络路径。按本 TaskPack 独立提交逆序回滚，不回滚 Phase 2 Contracts、Rate Limiter 或数据库历史。

# 百科通道回退：DBpedia Lookup（2026-11-04）

## 决策来源

Owner 2026-11-04 在“百科通道当前不可直连”的说明后选择：**先用其他免费百科源**。

## 事实与原因

- 本机对 `en.wikipedia.org`、`zh.wikipedia.org`、`api.wikimedia.org`、`www.wikidata.org` 的 8 秒直连均返回 `000`（TCP 超时）。
- 本机无监听中的 HTTP CONNECT 代理（7890/7891/7897/10809/1080/8080/8888），系统代理关闭。
- `https://lookup.dbpedia.org/api/search?query=...&maxHits=1&format=json` 可达（实测约 6–10 s，返回 `application/json`，含 `docs[].resource/label/comment`）。DBpedia 数据派生自 Wikipedia，按 CC BY-SA 3.0 发布，无需 key。

## 本次改动

- `services/python-workers/machine/public_research.py`：百科主通道仍为 Wikipedia；仅当 Wikipedia 通道处于可回退的失败态（`offline/network_unavailable`、`proxy_timeout`、`http_429`、`5xx`）时，追加 **dbpedia** 通道（`https://lookup.dbpedia.org/api/search?query=&maxHits=&format=json`），并保留失败的 Wikipedia 通道、原始响应与状态。DBpedia 的 `comment` 只作为 **excerpt/abstract** 表达，`locator=dbpedia:lookup;comment`，`license=CC BY-SA 3.0`，不绑定 revision。
- `crates/archeaxis-domain/src/public_research.rs`：为 `("encyclopedia","dbpedia")` 增加 request URL 精确参数校验、身份/URL/locator 校验、representation 校验与许可校验；允许在原有 family 数基础上多一条百科回退通道，并要求回退通道位于 Wikipedia 之后且主通道确实处于可回退失败态。
- 固定解析器身份随之更新（`public_research_identity.py` 与说明文档），因为整个 worker 文件字节发生变化。
- 登记 `docs/environment/EXTERNAL_DEPENDENCIES.md` 的 Wikipedia/DBpedia/Stack Exchange 行。

## 边界

- DBpedia Lookup 是 Wikipedia 的派生索引与外链（`https://dbpedia.org/resource/...`），**不代表 Wikipedia 全站覆盖**，也不证明正文完整性；摘要为提供方片段。
- `maxHits > 1` 时响应可能超过 worker 的 128 KiB 上限并记 `invalid_response`（不静默截断）；默认 limit=1 实测约 115 KB。
- 若未来代理可用或 Wikipedia 恢复可达，主通道仍优先，无需改产品行为。
- 单元测试为合成数据；真实网络证据另记唯一执行记录，安装态与 Owner 接受不由此得出。

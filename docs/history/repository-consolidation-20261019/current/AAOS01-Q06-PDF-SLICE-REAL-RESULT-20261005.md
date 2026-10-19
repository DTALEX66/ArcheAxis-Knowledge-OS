# AAOS-01 Q06 PDF 切片：候选内真实结果（2026-10-05）

本文件记录一次真实交付，不是核对说明。纠正指令指出 job kind 是 pdf（pdf.extract 是路由 capability），
据此重跑即通过。既有测试印证同一契约：`crates/archeaxis-application/tests/pdf_job_end_to_end.rs:99`
调用 `jobs::enqueue(conn, "job", "pdf", &source_id)`。

## 运行身份

| 项 | 值 |
| --- | --- |
| run_id | pdfs094114 |
| run 目录 | `.project-local/runs/pdf-slice-pdfs094114/`（含 receipt.json） |
| Core 可执行 | 候选 `.project-local/rt/core/archeaxis-api.exe` |
| 解释器 | 候选 `.project-local/rt/runtime/python/python.exe` |
| worker-profile | 候选 `worker-profile.json`，13 条声明路由随启动文档下发 |
| 输入 | 项目 golden fixture 生成的 PDF，1120 字节 |
| 输入 sha256 | `0f0ffc50c79d9d977efb925351ca1d64a063184e4bdd71507b9ac44992f7adcf` |

## 真实请求/响应

| 步骤 | 状态 | 响应 |
| --- | --- | --- |
| POST /api/v1/imports | 202 | source_id `src_f4eee107088575eabd4e19a7`；返回 sha256 与输入逐位相同 |
| POST /api/v1/jobs {job_id, kind:"pdf", input_ref} | 202 | `{"job_id":"pdf-pdfs094114","state":"queued"}` |
| POST /api/v1/jobs/pdf-pdfs094114/executions（idempotency-key + deadline_ms 120000） | 202 | `{"state":"running","replayed":false,"request_id":"exec-pdfs094114"}` |
| GET /api/v1/jobs/pdf-pdfs094114（1 次轮询） | 200 | `{"attempt":1,"error":null,"state":"succeeded"}` |
| GET …/outputs/text | 200 | 见下 |

## 产出

```
Golden Journey Evidence
Original SHA and anchored conversion
Criterion
Verified
Page Anchor
PASS
```

metadata：`byte_length 97`、`sha256 d620831f8985189b2e52fe4ed1dee74912bd5d2219f61604142c30965c000c39`、
`schema archeaxis.text/v1`、`media_type text/plain; charset=utf-8`、
`authority_effect candidate_or_measurement_only`、`uri job://output/d620831f…`。

正文与 golden fixture 内嵌文本逐字相符。

## 按指令口径的 PASS 分项

| 判据 | 状态 |
| --- | --- |
| 正确原件 | ✅ 输入 sha256 与返回 sha256 逐位相同 |
| succeeded | ✅ state=succeeded，error=null |
| 可读且匹配样本的正文 | ✅ 见上 |
| 真实引擎身份 | **未采集** —— 输出 metadata 未含引擎名，需另查 |
| 有效定位与损失记录 | **未查** —— anchors / transform / 损失回执未读 |
| 退出重启后同一结果可读 | **未验** |

**结论**：**PDF 提取切片通过**；按指令口径**不记**完整产品或全部 PDF 能力通过。

## 更正 Superseded 说明

先前几份 AAOS01 文档中「409 说明必须先把 job 迁出 queued」「execute 不是 worker 的路」为**推断**，
现被实测推翻：`claim()` 直接接受 queued，execute 返回 202 running。**以本文件为准**，历史文件保留不改写。

## 未做与边界

未手工改数据库状态；未放宽状态守卫；未无差别重试；未截取桌面令牌；未写官方 Green；未删任何文件。

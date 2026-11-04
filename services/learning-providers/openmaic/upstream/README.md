# OpenMAIC 1.3.0 上游源码快照

本目录是 **THU-MAIC/OpenMAIC 1.3.0 的完整上游源码快照**，由 Owner 2026-11-05 的“全量吸收、全量融入”指令加入。

## 身份

- 项目：`THU-MAIC/OpenMAIC`
- 版本：`1.3.0`
- 归档：`.project-local/archives/owner-inputs/20261101-learning-platform-sources/OpenMAIC-1.3.0.zip`
- 归档 SHA-256：`7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40`
- 文件数：3,830
- 解包字节：126,977,302（仓库快照 126,976,875，差异见下）
- 许可：MIT，`LICENSE` SHA-256 `ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19`
- 逐文件身份：`OpenMAIC-1.3.0-SOURCE-MANIFEST.json`

## 换行归一化

上游自带 `.gitattributes` 声明 `* text=auto eol=lf`。其中 3 个 Markdown 文件在归档中是 CRLF，Git 入库时会按上游规则归一化为 LF：

- `packages/@openmaic/importer/DESIGN.md`
- `packages/@openmaic/importer/SKILL.md`
- `packages/@openmaic/importer/src/serializer/textSerializer.md`

`SOURCE-MANIFEST.json` 对这 3 个文件记录的是仓库快照（LF）的字节数与哈希，并单列 `line_ending_normalization`；归档 ZIP 仍保留原始 CRLF 字节。

## 边界

- 本快照是**只读参考源**，不是 AAOS 的第二运行时、第二数据库或第二调度器。
- 本轮只完成源码吸收；Next 应用、渲染服务、PostgreSQL 持久化、Agent 与 `@openmaic/*` 包都没有被接线为产品真值。
- AAOS 的适配面仍在上一级目录（`services/learning-providers/openmaic/*`）；本快照不修改、不覆盖那些适配文件。
- Rust Core 仍是 SQLite/CAS 唯一 canonical writer；上游代码不得直接写产品数据库。
- 需要修改上游行为时，改适配器或引入新的版本化快照，不在本目录就地编辑。

## 验证

```text
sha256(archive) = 7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40
sha256(LICENSE) = ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19
files = 3830
```

`SOURCE-MANIFEST.json` 记录每个文件的相对路径、字节数与 SHA-256，并与归档字节绑定。归档原件保留在 Git 忽略区；本目录检出的是可直接审阅和适配的源码树。

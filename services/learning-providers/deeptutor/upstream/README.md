# DeepTutor 1.7.1 上游源码快照

本目录是 **HKUDS/DeepTutor 1.7.1 的完整上游源码快照**，由 Owner 2026-11-05 的“全量吸收、全量融入”指令加入。

## 身份

- 项目：`HKUDS/DeepTutor`
- 版本：`1.7.1`
- 归档：`.project-local/archives/owner-inputs/20261101-learning-platform-sources/DeepTutor-1.7.1.zip`
- 归档 SHA-256：`9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262`
- 文件数：4,471
- 解包字节：69,573,066
- 许可：Apache-2.0，`LICENSE` SHA-256 `cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4`
- 逐文件身份：`DeepTutor-1.7.1-SOURCE-MANIFEST.json`

## 边界

- 本快照是**只读参考源**，不是 AAOS 的第二运行时、第二数据库或第二调度器。
- 本轮只完成源码吸收；其 Web/Next 前端、Python 业务桥、旧数据库和 Agent 运行时都没有被接线为产品真值。
- AAOS 的适配面仍在上一级目录（`services/learning-providers/deeptutor/*.py`）；本快照不修改、不覆盖那些适配文件。
- Rust Core 仍是 SQLite/CAS 唯一 canonical writer；上游代码不得直接写产品数据库。
- 需要修改上游行为时，改适配器或引入新的版本化快照，不在本目录就地编辑。

## 验证

```text
sha256(archive) = 9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262
sha256(LICENSE) = cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4
files = 4471
```

`SOURCE-MANIFEST.json` 记录每个文件的相对路径、字节数与 SHA-256，并与归档字节绑定。归档原件保留在 Git 忽略区；本目录检出的是可直接审阅和适配的源码树。

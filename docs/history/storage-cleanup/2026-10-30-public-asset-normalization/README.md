# 公共人物素材副本归一 — 2026-10-30

Owner精确清理授权及root独立复核后，退役 `assets/astryn/` 下126个公开同字节文件（124 PNG、2 Markdown），保留 `assets/astryn-full/` 同相对路径、原件ZIP、全部目录及私有/未跟踪状态。仅更新现有 companion PROVENANCE custody说明及path-disposition note；未部署或执行donor。

126个精确路径减少459,018,818逻辑字节，不是Git对象或NTFS物理回收量。源文件在全量核验后以独占读/删除句柄保持闲置与身份，同句柄标记删除，父目录句柄阻止重命名；durable intent与逐项fsync journal保留。失败即停止，不递归操作目录。

独立后读回确认126源路径缺失、126保留件SHA、75归档对象CRC/SHA、原ZIP/manifest身份及2元数据预期内容。部署run因实际源码变化而记录 `INVALIDATED/source_consistent=false`（child exit0、receipt exit3、外层exit1），不是只读资格PASS。后继只读资格和原静态/browser-smoke结果沿MANIFEST的canonical收据查询。

`restore-map.json`为轻量原路径→保留件→原件成员→SHA映射；恢复前拒绝已有不同内容，不覆盖未知目标，不运行donor。完整外部源码/云端迁移、能力吸收、原生安装态与Owner验收均不由本次归一代替。

后继[独立复核与门槛记录](VERIFICATION.json)：root再次核126缺失、126保留SHA及75归档对象；115定向测试及原13视口/5主题browser-smoke通过。浏览器为SIMULATED_HOST_CORE_FIXTURE，不是原生安装态。worktree约定的126未暂存缺失及47存量CRLF原结果保留；最终Git候选按既有`--source index`单独验，不修改冻结原件或放宽规则。

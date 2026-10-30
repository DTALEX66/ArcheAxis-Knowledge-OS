# Legacy backup/restore probe：规范落点修复与实际仓库验证

本次修复正式入口 `scripts/probes/backup_restore_probe.py`：原入口固定使用 `.project-local/runs/backup-restore-probe-run`，启动时请求删除旧同名目录；现使用现有 `dev.artifact_directory` 在当前worktree/run的 `artifacts/backup-restore-probe/<uuid>/` 内分配。主业务逻辑未改，不增加新Runtime或目录豁免。

## 实际验证

源码HEAD `f5d8b570409ba6b0a1915fa7ab336c4be1879485`，三文件稳定dirty patch SHA `2ce0aa81962609e0f867975c18db68f68b134b47d17d8b9005dbd351fe97e55c`，验证前后相同。实际源码文件SHA `34b3c51ca62fc0a9cfda2c869aa0135a7549bff1df4db90e29a95ddb3e327b8b`，与已审候选一致。

实际仓库原有 `tests/test_backup_restore_probe.py` 8项通过，pytest退出0；未替换测试的PROBE路径，记录到实际调用正式源码的CLI退出0。测试运行有1条既有 `Unknown config option: cache_dir` 警告，未改配置掩盖。

只观察本run精确namespace，实际捕获1个UUID目录，source/target均出现、无reparse；运行后该次自有临时目录已由probe清理。旧固定目录前后都不存在，没有改动旧资料。Python Ruff现有门槛 `E9/F63/F7/F82` 退出0；三处dirty路径 `git diff --check` 退出0。两处Rust文件不适用Python Ruff，本记录不宣称其编译或Teaching API资格。

证据层是 **实际Python legacy备份/恢复驱动、独立合成库**：新库迁移、备份、目标初始化、恢复及冷读回由原业务测试执行。没有使用或复制Core载荷，没有真实资料、API或模型调用；不能写成Rust Core、安装态、完整CL/J或Owner验收通过。

## 早期证据与散落资料

`nrm-scatter2` 保留旧分配前缀RED→GREEN与拦截删除的sentinel证据；`nrm-scatter5` 是候选CLI显式绑定8tests的证据，层次与本次“实际正式源码、未覆盖PROBE路径”不同。原候选patch因CRLF上下文无法直接apply时，root另派生LF patch；原候选与旧patch不改写，最终源码SHA如上。

三组历史build/stage脚本共6份、23,781B仅做过保全副本候选，原件未迁移或删除，回收0B；不得称目录规范化或清理整体完成。相同大小的c453 runner脚本实际SHA/回调版本不同，保留、不视为重复。

MANIFEST钉本次及早期本地收据SHA/退出码。全部公开候选为UTF-8 LF；原始详细证据继续位于ignored目录。剩余散落债和未知归属保留，本次未扩扫描或读取既有真实DB及会话正文。

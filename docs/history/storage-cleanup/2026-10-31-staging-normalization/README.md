公开staging叶文件归一：清理前恢复导航（部署待执行）

本记录只登记已核验的精确候选和历史恢复路径。尚未删除文件；部署事实以随后独立canonical intent、逐项journal和事后核验为准。候选基于f10dedee225ad7b049b99668d3c3a43d8d105bd8；后续提交只改变公开导航时，仍须在新run重新核资格。

| 精确来源 | 同SHA独立保留位置 | 文件数 | 逻辑B |
| --- | --- | ---: | ---: |
| `.project-local/runs/be268a2d33/cnprep2/artifacts/package/` | `.project-local/runs/be268a2d33/cnprep3/artifacts/package/` | 14 | 452771641 |
| `.project-local/runs/be268a2d33/cnprep2/artifacts/pwsh/` | `.project-local/runs/be268a2d33/cnprep3/artifacts/pwsh/` | 657 | 256592821 |
| `.project-local/runs/be268a2d33/cppns1/artifacts/p/target/release/`中逐项登记的公开payload | `.project-local/runs/be268a2d33/cppns2/artifacts/p/target/release/`对应成员 | 19744 | 1405364297 |
| 合计 | 只限逐文件清单，不按目录递归操作 | 20415 | 2114728759 |

逐文件来源、保留位置、完整SHA及双方身份在`.project-local/runs/be268a2d33/spr-stageaudit2/artifacts/candidate-files.jsonl`，SHA256 `6535455ebf3395f08db1f0f202792d69cafe720405f814a361fd596fcc806711`。目录不会递归删除；未列成员保持。预估数为路径逻辑字节，不是Git对象或物理磁盘释放。

cnprep2的package setup.exe副本包含在14项候选中；cnprep3中的同SHA setup.exe保留，cppns1和cppns2各自原始NSIS installer均不在候选。不能把本批描述成所有安装器都不动。全部input和output、2个PEM、打包依赖中的1个.agents命名成员、独有失败/成功证据、identity/proof/log/config及其他HOLD根保持；仅按名称保留，不声称已检查这些成员内容。

历史消费者按本导航解析保留件：cnprep2原WSB和full-inputs保持原字节，清理后冻结；如需重放，先从保留件逐项核SHA并排他创建缺失的原路径，恢复671项，再核完整原manifest、配置、当前权限与闲置。禁止覆盖不同内容或改写旧清单绕过检查。cnprep3本批未失去任何文件，不因本次归一需要恢复；未来复用仍须fresh完整资格。prepare-v2/v3的固定PACK来源cppns2保持完整。

cppns1原CLI为exit0，但最终POSTCHECK因unsafe bundle root失败；其原FAIL、安装器、identity、proof、日志和配置保持。重放原bundler前须按同一map恢复19744项；原失败不会改成PASS。cppns2原后继成功和所有消费者/回滚材料保留。

spr-stageaudit2为文件保全链的LOCAL_PASS/source_consistent=true；未证明未来部署闲置、native replay、产品或Owner验收。部署前必须核当前map/support身份、完整SHA及对象边界、官方沙盒库存和当前消费者/进程闲置，使用父目录pins、同对象句柄、durable intent和逐项journal；不合格项保留，不停止其他进程。

MANIFEST绑定纠正后的恢复合同。它纠正早期候选中将cnprep3也写成清理后缺输入冻结、以及笼统“安装器保留”的描述；原回执和逐项map不改。

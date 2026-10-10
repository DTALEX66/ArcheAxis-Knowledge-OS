// Generated from the recorded crosswalk/qualification/ledger/freeze bytes. No runtime authority.
export type ResourceJson = null | boolean | number | string | ResourceJson[] | { [key: string]: ResourceJson };
export type ResourceObject = { [key: string]: ResourceJson };
export type ResourceClass = "enableable_plugin" | "absorbed_algorithm" | "ux_donor" | "format_spec" | "base_dependency" | "future_candidate" | "not_adopted";
export type ResourceEvidence = { state: string; value: ResourceJson; source_refs: { path: string; sha256: string }[] };
export type ResourceQualification = { stable_key: string; disposition: string; reason: string; activation: { state: string; conditions: ResourceJson; scope: ResourceJson }; evidence: { version: ResourceEvidence; license: ResourceEvidence; permissions: ResourceEvidence; runtime: ResourceEvidence; qualification: ResourceEvidence; source_refs: ResourceJson }; [key: string]: ResourceJson };
export type ResourceEntry = { stable_key: string; display_names: string[]; surface_class: ResourceClass; absorption_mode: string; classification_reason: string; declared_runtime_route: string | null; original_surface: ResourceObject; ledger: ResourceObject | null; qualification: ResourceQualification };
export type ResourceCatalog = { schema: string; sources: { path: string; sha256: string }[]; crosswalk_metadata: ResourceObject; qualification_metadata: ResourceObject; freeze_register: ResourceObject; entries: ResourceEntry[] };
export const RESOURCE_CATALOG: ResourceCatalog = {
  "schema": "archeaxis.resource-catalog-projection/v1",
  "sources": [
    {
      "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
      "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
    },
    {
      "path": "docs/current/AAOS-RESOURCE-QUALIFICATION-20261010.json",
      "sha256": "4550795e5d19ea60b3fc322f1e57bad1e2971c5042774df8dee7c6b668a7f7a7"
    },
    {
      "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
      "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
    },
    {
      "path": "docs/taskpacks/aaos-ui-first-20261009/FREEZE-REGISTER.json",
      "sha256": "177e6d0ba6b56beb7606b3a7127bb9f5013ba805c79d3d2db628d2fe4ba38edb"
    }
  ],
  "crosswalk_metadata": {
    "schema": "archeaxis.oss-absorption-surface-crosswalk/v1",
    "artifact_name": "oss-absorption-surface-crosswalk-20261008",
    "observed_at": "2026-10-08",
    "baseline": "4b9828c4058901c0b1fd2c75c528238c55e0ec89",
    "purpose": "One honest surface_class per open-source absorption entry, joining the A-E reuse-verification vocabulary to the capability absorption registry's allowed_absorption_modes, so the UI can show absorption sources without rendering all of them as enable-able plugins.",
    "generator": {
      "path": "scripts/audit/build_oss_absorption_crosswalk.py",
      "sha256": "f4802c4f4be790fef0ca385fc528211992714f91c7edebbe4af0c57df555d45c"
    },
    "producing_command": [
      "<python>",
      "scripts/audit/build_oss_absorption_crosswalk.py",
      "--root",
      "<repository root>",
      "--output",
      "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json"
    ],
    "entry_universe": {
      "oss_reuse_decisions": 39,
      "capability_absorption_registry": 11,
      "supply_chain_ledger": 51,
      "grouped_entries": 68,
      "excluded": "The 369-row historical research pool and the 691-row lossless crosswalk it produces. Those rows are candidate names, not absorption entries (docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json: '369 pool entries are not 369 installations'); they stay in the regenerated payload described by docs/current/OSS-REUSE-CROSSWALK-20261008.manifest.json, which this artifact does not replace."
    },
    "id_namespaces": {
      "capability_atlas": {
        "pattern": "^CAP-[0-9]{4}$",
        "owner": "docs/truth/CAPABILITY_ATLAS_V2.yaml",
        "state_owner": "config/capability-map.v1.json",
        "count": 16,
        "ids": [
          "CAP-0010",
          "CAP-0020",
          "CAP-0030",
          "CAP-0040",
          "CAP-0050",
          "CAP-0060",
          "CAP-0070",
          "CAP-0080",
          "CAP-0090",
          "CAP-0100",
          "CAP-0110",
          "CAP-0120",
          "CAP-0130",
          "CAP-0140",
          "CAP-0150",
          "CAP-0160"
        ]
      },
      "capability_absorption_registry": {
        "pattern": "^CAP-[A-Z][A-Z0-9-]+$",
        "owner": "docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml",
        "count": 11,
        "ids": [
          "CAP-CORE-KNOWLEDGE",
          "CAP-DEEPTUTOR",
          "CAP-OPENTUTOR",
          "CAP-LEARNINGMAP",
          "CAP-OPENMAIC",
          "CAP-RAG-ANYTHING",
          "CAP-LIGHTRAG",
          "CAP-GRAPHITI",
          "CAP-MEMOS",
          "CAP-WEKNORA",
          "CAP-COGNEE"
        ]
      },
      "warning": "The registry's schema pattern ^CAP-[A-Z0-9-]+$ also matches an atlas id such as CAP-0010, so pattern checking alone cannot separate the namespaces. The atlas column is validated against the atlas id set and the registry column against the registry id set.",
      "never_merge": true
    },
    "surface_classes": {
      "enableable_plugin": "Bound to a real capability lifecycle: an atlas capability id that exists in docs/truth/CAPABILITY_ATLAS_V2.yaml, a state in config/capability-map.v1.json, and donor-specific adoption evidence. The only class the UI may render as an enable-able source.",
      "absorbed_algorithm": "The donor's behaviour is carried in product code, but no capability lifecycle handle binds it (no atlas join, an undeclared route id, a legacy-path binding, or a route served by a different engine). Real, and not a plugin.",
      "ux_donor": "Carried in the client/UI layer or declared as a UX donor: it shapes an interaction instead of serving a capability route.",
      "format_spec": "A format/protocol/contract reference that was extracted rather than installed; tier C means no runtime adoption is implied.",
      "base_dependency": "Substrate: a declared package, a vendored copy, a bound external tool, or first-party core that the product runs on and does not expose as an enable-able source.",
      "future_candidate": "Deferred: a stated value and demand trigger with no adoption record.",
      "not_adopted": "Not adopted for the stated role: tier E, REJECT-CORE/REVIEW-BLOCK with nothing carried, or a claimed adoption whose donor artifact is absent."
    },
    "derivation": {
      "verification_tier": "the category scripts/audit/build_oss_reuse_inventory.py carries for this entry's records; B is promoted to A only by bound verification in docs/current/OSS-REUSE-VERIFICATION-20261008.json, never by a decision",
      "absorption_mode": "declared values are kept per namespace and never overwritten; derived_mode is computed from the artifact shape in the registry's own vocabulary",
      "atlas_capability_id": "the entry's dotted capability id appearing in config/capability-map.v1.json runtime_capabilities, or the donor name appearing in docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies; two different matches make the row a conflict and refuse the plugin class",
      "adoption": "donor-specific terms only. Tokens that are the capability's own name or acronym are stripped first, then probed as declared package names (pyproject.toml, uv.lock, requirements.txt, frontend/package.json, frontend/package-lock.json, Cargo.lock), vendor roots, first-party source identifiers excluding self-declared unavailable stubs, the bound external resource index, and the declared route worker files",
      "surface_class": "ordered rules in derive_surface_class; enableable_plugin additionally requires an atlas id in the atlas set, a capability-map state, a carried donor artifact, tier A or B, and a route binding that names the donor in the declared worker. The generator raises rather than emitting a table containing an unentitled plugin row."
    },
    "class_counts": {
      "base_dependency": 20,
      "absorbed_algorithm": 16,
      "future_candidate": 10,
      "enableable_plugin": 7,
      "not_adopted": 11,
      "format_spec": 3,
      "ux_donor": 1
    },
    "class_order": [
      "enableable_plugin",
      "absorbed_algorithm",
      "ux_donor",
      "format_spec",
      "base_dependency",
      "future_candidate",
      "not_adopted"
    ],
    "conflict_count": 115,
    "entries_with_conflicts": 59,
    "inputs": {
      "docs/current/OSS-REUSE-DECISIONS-20261008.json": {
        "sha256": "ba938bc36d74551a08b7ab94b4b1513122b4d853353e6d41c15feedab86cbe38",
        "bytes": 23384
      },
      "docs/current/OSS-REUSE-VERIFICATION-20261008.json": {
        "sha256": "67c25efebac6d42ab4a20e82c27b4f771acaffeafff0a5d913cab38b45ae2cf0",
        "bytes": 14105
      },
      "docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml": {
        "sha256": "a5241e1f2e2ec634e957bcd2551dc78eefe216c596b91f08181b4ba5f5d046a8",
        "bytes": 11968
      },
      "config/schemas/capability-absorption-registry.schema.json": {
        "sha256": "6a379825d6c27dd71d81aaadd73644237ea13f305c3797a6e0bdcef7c50ef1ce",
        "bytes": 3291
      },
      "docs/truth/SUPPLY_CHAIN_LEDGER.json": {
        "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169",
        "bytes": 49176
      },
      "docs/truth/CAPABILITY_ATLAS_V2.yaml": {
        "sha256": "c290b342f47d38e79f3e1539175d21f822808495a902b465ea1b0d42b99cc39a",
        "bytes": 10318
      },
      "config/capability-map.v1.json": {
        "sha256": "d5873a524c04d5b6213dbd3f5f39d20c0056e5fc96e4d3c977daf7d4f572ed0e",
        "bytes": 2987
      },
      "services/python-workers/routes.json": {
        "sha256": "0ac3068fe9a9179eb6575609305d3eaf88e7d9d485a0794b7948333c0a70706f",
        "bytes": 1378
      },
      "config/environment/external-resources-index.json": {
        "sha256": "8d5f9d30c7f7585d9dc7db1f6476d5ee2c418a2b6ea656c88bfe1c1b922d7cd2",
        "bytes": 77157
      },
      "docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json": {
        "sha256": "29810dc3978cd90f4bcf8a8859e489655d3a52ff564eabb80ae17c52a82d2917",
        "bytes": 11591
      },
      "scripts/audit/build_oss_reuse_inventory.py": {
        "sha256": "8cc1af1e2b78614026a0856863ff221c07b7539833eb23b47679fa99f962db79",
        "bytes": 8562
      },
      "scripts/audit/oss_disposition_evidence.py": {
        "sha256": "4900fd22b84ba7ba5f05a56ec52510c63b7a8ca7e21de073abf8dec1c2f71de2",
        "bytes": 18439
      }
    },
    "limits": [
      "A row's class is what the tracked files support today, not what a plan intends.",
      "NOT_RUN stays NOT_RUN: nothing here proves installed-desktop or release qualification.",
      "Donor joins are exact-normalized only. A donor spelled differently across sources stays two rows rather than becoming one merged claim.",
      "shared-contracts/ and inspiration_research/ are outside the source roots the donor check scans, so an adapter kept only there reports no artifact.",
      "The registry's CAP-XXX ids and the atlas's CAP-00NN ids are separate namespaces; this table never copies one into the other's column."
    ]
  },
  "qualification_metadata": {
    "schema": "archeaxis.resource-qualification-overlay/v1",
    "observed_at": "2026-10-09T22:02:38.098939+00:00",
    "selected_scope": [
      "archeaxiscoreknowledge",
      "capcoreknowledge",
      "fsrs",
      "jsoncanvas",
      "jsonschemaspec",
      "prosemirror",
      "pymupdf",
      "tiptap",
      "trafilatura"
    ],
    "sources": [
      {
        "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
        "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
      },
      {
        "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
        "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
      },
      {
        "path": "docs/current/OSS-REUSE-VERIFICATION-20261008.json",
        "sha256": "67c25efebac6d42ab4a20e82c27b4f771acaffeafff0a5d913cab38b45ae2cf0"
      },
      {
        "path": "uv.lock",
        "sha256": "0e3db03c3dcd71e24acc13022839591b575f10e42f1dbdfde8b86ec77fc8f2e3"
      },
      {
        "path": "frontend/package-lock.json",
        "sha256": "bad160497be687b50a3c03241942fce9fff5741f7f2657dc5da953baace48897"
      },
      {
        "path": "Cargo.lock",
        "sha256": "8cb82278834c9c1ec20fc27529810270d1d8157cfbe398c991d223f95e3e849b"
      },
      {
        "path": "src-tauri/Cargo.lock",
        "sha256": "370731e01e29db9b97448ed872d131dec0abd288a2f779dcfe9d8f3273e3bfc4"
      },
      {
        "path": "THIRD_PARTY_NOTICES.md",
        "sha256": "8d15693693371a22ef5fb157de83523af576718338f914855a2dc1c075c7f260"
      },
      {
        "path": "scripts/release_sbom.py",
        "sha256": "528ba4d3bdd95496101060211cc374fecfcd2f2ba3debd947b948b1aeda6f041"
      },
      {
        "path": "docs/taskpacks/aaos-ui-first-20261009/TASKS.json",
        "sha256": "1dbc0b24375df5f2b4897bf88fa6cf3fd4a4b3e0dfc114bc5d96b5a362eea169"
      }
    ],
    "limits": [
      "No runtime was executed by this assessment",
      "68 inherited rows and 115 conflicts unchanged",
      "No professional/human/installed/release qualification",
      "CoreDocument does not introduce an invented 69th donor",
      "Public official HEAD readback is not exact locked-package license byte validation"
    ],
    "source_readback_updated_at": "2026-10-09T22:12:34.749092+00:00",
    "readback_boundary": "Source SHA refreshed after current template validator integration; runtime/model/installed qualification is not promoted."
  },
  "freeze_register": {
    "status": "LOGICAL_FREEZE_ONLY",
    "physical_files_moved_or_deleted": 0,
    "original_bytes_preserved": true,
    "rows": [
      {
        "id": "FORMAL-AVALONIA",
        "target": "R6/旧母版 Avalonia正式实施与 MainWindow 重构顺序",
        "reason_class": "SUPERSEDED_EXECUTION",
        "reason": "正式 Tauri+React 路线来自 writer 当前 AGENTS/SUP-022；原 Avalonia donor/恢复代码保留。",
        "activation_condition": "具体供体行为复用，不再续写正式 Avalonia UI"
      },
      {
        "id": "OLD-RUN-ORDER",
        "target": "R1/R2/R3/R5/R6/M0 旧整包自动排队",
        "reason_class": "SUPERSEDED_SEQUENCE",
        "reason": "旧序列不能压过当前 UI 优先用户决定；旧有效约束和能力分别合并到新切片。",
        "activation_condition": "当前权威逐条选入，不复活整包"
      },
      {
        "id": "EVIDENCE-SAVE-GATE",
        "target": "普通笔记必须依据/云核验/人审才能保存",
        "reason_class": "SUPERSEDED_APPLICABILITY",
        "reason": "新来源和用户产品决定普通内容先保存；专业采纳和高风险执行仍独立受控。",
        "activation_condition": "普通保存不再作为可重启门槛；证据核查用于其实际场景"
      },
      {
        "id": "MOCK-FALLBACK",
        "target": "原型 localStorage/innerHTML/演示 KPI 当真实业务",
        "reason_class": "REJECTED_IMPLEMENTATION_ROUTE",
        "reason": "参考原型只提供布局交互；真实业务必须通过唯一 Core writer。",
        "activation_condition": "不能激活；仅可借用视觉设计"
      },
      {
        "id": "T0-T5-REDO",
        "target": "按旧 Qoder 清单重新开发已被 Codex 修复的 T0–T5",
        "reason_class": "DUPLICATE_EXECUTION",
        "reason": "保留现有本地修复与回归，下一切片只做兼容回归/真实未验项目。",
        "activation_condition": "出现当前快照回归证据时定向修复"
      },
      {
        "id": "TEMPLATE-PAGING-REDO",
        "target": "重新做已存在 cursor 分页/第二模板 DB",
        "reason_class": "DUPLICATE_EXECUTION",
        "reason": "现有 bindings 分页及真实 Core 模板 persistence 是供体；未知资格补测试。",
        "activation_condition": "现有实现确实失败才最小修复"
      },
      {
        "id": "UI-OLD-TRUNCATED",
        "target": "原单包 UI 截断文件和重复索要补交",
        "reason_class": "SUPERSEDED_INPUT",
        "reason": "四份新 UI 补交有哈希与完整内容；旧文件保留为历史问题。",
        "activation_condition": "仅历史字节恢复/审计，不作本次完整源"
      },
      {
        "id": "ALL-OSS-INSTALL",
        "target": "全装 369 池/691 来源行即完成集成",
        "reason_class": "UNSELECTED_DONOR_EXECUTION",
        "reason": "按所需组件与实际供体模式复用，完整池能力意图保留。",
        "activation_condition": "选定具体能力、许可证、预算及环境后 O01"
      },
      {
        "id": "CROSS-REPO-WRITE",
        "target": "自动写 DESIGN-LAB/WORK-LAB 或共用 DB",
        "reason_class": "OUTSIDE_CURRENT_SCOPE",
        "reason": "本轮规划/后续 AAOS 默认 slice 只在 AAOS；可给人工交换提示词，不能代发消息。",
        "activation_condition": "对方项目独立任务与明确授权"
      },
      {
        "id": "PRIVATE-SESSION-MIGRATE",
        "target": "读取私人 Agent memory/session 为凑齐对话",
        "reason_class": "OUTSIDE_CURRENT_SCOPE",
        "reason": "当前只整理可见用户对话及提供档案。",
        "activation_condition": "必须明确 exact source+operation 专门授权"
      },
      {
        "id": "ADVANCED-ENGINES",
        "target": "仿真/3D/VR/AR/XR/训练/一般编排重型实施",
        "reason_class": "FUTURE_INTENT_PRESERVED",
        "reason": "FT01–FT04 能力发现保留，优先完成真实 UI/学习主线。",
        "activation_condition": "明确选定未来切片并核资源/依赖/验收"
      },
      {
        "id": "PAUSED-CI",
        "target": "先前被用户停止的本地/云端 CI 工作",
        "reason_class": "PAUSED_EXECUTION_PRESERVED",
        "reason": "dirty 实现保留；规划不恢复本任务。",
        "activation_condition": "单独选中 V01 才执行；远程/付费另需授权"
      },
      {
        "id": "STORAGE-BULK-DELETE",
        "target": "依据历史体积一键清理整仓/Green/外溢",
        "reason_class": "NO_BULK_DELETE_GRANT",
        "reason": "先 S01 当前计量与精确清单；本轮逻辑归档不搬走原文件。",
        "activation_condition": "当前 exact-path reviewed scope 与明确删除授权"
      }
    ]
  },
  "entries": [
    {
      "stable_key": "antiword",
      "display_names": [
        "msys2/MINGW-packages/tree/master/mingw-w64-antiword",
        "antiword (probed sidecar binary)"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "antiword",
        "display_names": [
          "msys2/MINGW-packages/tree/master/mingw-w64-antiword",
          "antiword (probed sidecar binary)"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "msys2/MINGW-packages/tree/master/mingw-w64-antiword",
            "capability_id": "office.doc"
          },
          "supply_chain_ledger": {
            "id": "A025",
            "capability": "document-legacy"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": null
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "SIDECAR",
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "mingw-w64-antiword",
            "mingw_w64_antiword",
            "antiword"
          ],
          "hits": {
            "imported_in_source": {
              "antiword": [
                "services/python-workers/document/worker_office.py:64"
              ]
            },
            "tool_invoked": {
              "mingw-w64-antiword": [
                "antiword",
                "antiword-mappings",
                "services/python-workers/document/worker_office.py:14",
                "services/python-workers/tool_paths.py:54"
              ],
              "mingw_w64_antiword": [
                "antiword",
                "antiword-mappings",
                "services/python-workers/document/worker_office.py:14",
                "services/python-workers/tool_paths.py:54"
              ],
              "antiword": [
                "antiword",
                "antiword-mappings",
                "services/python-workers/document/worker_office.py:14",
                "services/python-workers/tool_paths.py:54"
              ]
            },
            "mentioned_only": {
              "antiword": [
                "services/python-workers/tool_paths.py:54"
              ]
            }
          },
          "bound_resource_entries": [
            "antiword",
            "antiword-mappings"
          ],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "document-legacy",
            "office.doc"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['document-legacy', 'office.doc'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "document-legacy",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "office.doc",
              "declared_runtime_capabilities_in_the_same_domain": [
                "office.structure"
              ],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A025",
        "name": "antiword (probed sidecar binary)",
        "version": "MSYS2 packaging 0.37-3; the binary self-reports 'Version: 0.37  (21 Oct 2005)'",
        "canonical_url": "https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-antiword",
        "capability": "document-legacy",
        "code_license": "GPL-3.0-or-later per the MSYS2 package index ([\"GPL3+\"]); the binary self-reports 'Status: GNU General Public License' without naming a version",
        "model_license": null,
        "disposition": "SIDECAR",
        "qualification": [
          "installed"
        ],
        "product_path": "services/python-workers/document/worker_office.py",
        "evidence": "Bound as a declared external engine on this host, not merely probed. Two entries were added to `config/environment/capability-requirements.yaml` and regenerated into `config/environment/external-resources-index.json` with `exists: true` for both: `antiword` -> `D:\\All projects\\OS External Configuration\\10-toolchains\\antiword\\antiword.exe` (284448 bytes, sha256 `d30a37489c64ada474d8d5aa5abb0778a6955d3ce6cdbb7c8c659e37b89d3da9`, byte-identical to the Git-for-Windows copy at `C:\\Program Files\\Git\\mingw64\\bin\\antiword.exe`, 284448 bytes, sha256 `d30a37489c64ada474d8d5aa5abb0778a6955d3ce6cdbb7c8c659e37b89d3da9`), and `antiword-mappings` -> `D:\\All projects\\OS External Configuration\\10-toolchains\\antiword\\.antiword` (30 `*.txt` tables, 306272 bytes, UTF-8 table present: true). The second entry is not decoration and is the reason this row changed at all: antiword looks for its character mapping only in `$HOME/.antiword` and `/usr/share/antiword`, a mapping named by absolute path is truncated to the engine's buffer and its default table is used instead (measured), and a copy outside the install tree fails with \"I can't open your mapping file (UTF-8.txt)\" - exit 1, zero output - so the tables directory must be declared and its parent handed to the process as HOME. `worker_office._antiword_mapping_home()` does exactly that and records `mapping_home` in the loss receipt; with nothing declared it leaves the environment untouched, which is what keeps an in-place install working and keeps CI honest. Measured through the real reader: tests/workers/test_doc_engine.py 18 passed on this host, including the declared-pair case and the two end-to-end cases that call `_doc_text` on the real Word file while the declaration is what resolves. The binary is still not bundled and still not installed by this repository; `probe` for it is the generic registry prober appending `--version`, which antiword answers with its usage text and exit 1, so the inventory shows `available: true, probe: probe_failed` for this engine - stated here because a passing resolution and a failing generic probe are both true at once.",
        "decision": "Isolated, removable sidecar for `.doc` only, now bound by declaration to the external tool root instead of resolved by PATH luck. Not a core dependency, not bundled, not installed by this repository and not relicensed by it; it never replaces the main conversion chain. The copy under `10-toolchains/antiword/` is a local placement of the Git-for-Windows binary: if that package updates, the placed copy does not follow it, and the row's sha256 is the identity to compare against before trusting either. `.ppt` stays unprovided: the JVM-backed candidate cannot be qualified without a system-level runtime install, which the current boundary forbids.",
        "upstream_note": "Upstream stated by the package index: http://www.winfield.demon.nl/ (not fetched from this run; the packaging repository above is the source of record here). Repositories carrying the package: clang64, clangarm64, ucrt64 - note the Git-for-Windows copy measured here is from its mingw64 bundle."
      },
      "qualification": {
        "stable_key": "antiword",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "MSYS2 packaging 0.37-3; the binary self-reports 'Version: 0.37  (21 Oct 2005)'",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "GPL-3.0-or-later per the MSYS2 package index ([\"GPL3+\"]); the binary self-reports 'Status: GNU General Public License' without naming a version",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "installed"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "apachetika",
      "display_names": [
        "apache/tika",
        "Apache Tika"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "no single atlas capability joins it: capability ids ['document-legacy', 'office.ppt'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "apachetika",
        "display_names": [
          "apache/tika",
          "Apache Tika"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "apache/tika",
            "capability_id": "office.ppt"
          },
          "supply_chain_ledger": {
            "id": "A010",
            "capability": "document-legacy"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A010"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "SIDECAR",
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "tika",
            "Apache Tika"
          ],
          "hits": {
            "imported_in_source": {
              "tika": [
                "services/python-workers/document/worker_office.py:73"
              ]
            },
            "tool_invoked": {
              "tika": [
                "apache-tika",
                "services/python-workers/document/worker_office.py:77",
                "services/python-workers/tool_paths.py:57"
              ],
              "Apache Tika": [
                "apache-tika",
                "services/python-workers/document/worker_office.py:77",
                "services/python-workers/tool_paths.py:57"
              ]
            },
            "mentioned_only": {
              "Apache Tika": [
                "services/python-workers/document/worker_office.py:772",
                "crates/archeaxis-application/src/attempts.rs:297"
              ],
              "tika": [
                "services/python-workers/tool_paths.py:57",
                "services/python-workers/transport/text_ndjson.py:346",
                "crates/archeaxis-application/src/attempts.rs:297"
              ]
            }
          },
          "bound_resource_entries": [
            "apache-tika"
          ],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "document-legacy",
            "office.ppt"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['document-legacy', 'office.ppt'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['document-legacy', 'office.ppt'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "document-legacy",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "office.ppt",
              "declared_runtime_capabilities_in_the_same_domain": [
                "office.structure"
              ],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A010",
        "name": "Apache Tika",
        "canonical_url": "https://github.com/apache/tika",
        "capability": "document-legacy",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "SIDECAR",
        "qualification": [
          "source",
          "installed"
        ],
        "decision": "Legacy/rare format rescue sidecar for `.ppt` only, resolved as a pair: a JVM and the Tika jar, each declared in `config/environment/capability-requirements.yaml` (`zulu-jre`, `apache-tika`). Declaring only the jar would resolve and then fail, which is the same shape as the antiword mapping-table trap. Not a primary engine, not bundled, not installed by this repository, and it does not replace the main conversion chain; an unresolvable pair is a named failure that projects nothing.",
        "upstream_note": "1000+ formats claimed upstream; only the `.ppt` text path is asserted here, and only because a real legacy presentation was read through it on this host.",
        "version": "4.1.0 (tika-app distribution)",
        "product_path": "services/python-workers/document/worker_office.py",
        "evidence": "Installed and exercised on this host, not merely catalogued. The official Apache distribution `tika-app-4.1.0.zip` (55,617,982 bytes, sha512 `e8ffd4b85f08b2c96790cbb8c7679ec29c41f10e4add8a72ca2047ca56b450e198c0671ca0517c977c00d3a95a9c08dc0b026ee9379e67d35e92425487c8745d` as published beside it) was placed under the declared external tool root and verified byte-for-byte before use; the runnable jar inside it is `10-toolchains/tika/4.1.0/tika-app-4.1.0.jar`, 122724 bytes, sha256 `4344806e966fef4d0d75f4f977b17ff745cf935e8138de7f5ed845ee2de76bd5`, with `lib/` and `plugins/` beside it and its own `LICENSE` read as Apache-2.0 rather than assumed. `java -jar … --version` answers `Apache Tika 4.1.0`, and the worker's own declared lane read a genuine PowerPoint 97 file (`tests/fixtures/golden/golden-ppt-anchor.ppt`, 16,384 bytes, sha256 `499ccd0de7c0778afa4f6ed08793afd2406b62547373a619a5a78658ae65c4b7`, the Apache Tika microsoft-module test document at the pinned release tag 3.3.2, whose commit is recorded in tests/fixtures/golden/manifest.json) into the projection `Sample Powerpoint Slide / Created with Microsoft Powerpoint X for Mac Service Release 1`. tests/workers/test_ppt_engine.py 12 passed on this host, and its real-engine case skips with the resolver's own reason where the pair is absent - a statement about the host, not a pass. Measured trap that shapes the code: Tika's CLI writes its startup notice to stderr and the document text to stdout, so a projection built from both streams would be noise; the notice also says single-file CLI mode turns on several non-default features (TIKA-2374, TIKA-4017, TIKA-4354, TIKA-4472), which is stated in the loss receipt instead of hidden."
      },
      "qualification": {
        "stable_key": "apachetika",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "4.1.0 (tika-app distribution)",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source",
                "installed"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "apscheduler",
      "display_names": [
        "agronholm/apscheduler",
        "APScheduler"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "apscheduler",
        "display_names": [
          "agronholm/apscheduler",
          "APScheduler"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "agronholm/apscheduler",
            "capability_id": "legacy.runtime.scheduler"
          },
          "supply_chain_ledger": {
            "id": "C012",
            "capability": "scheduling"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "C012"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "apscheduler",
            "APScheduler"
          ],
          "hits": {
            "package_declared": {
              "apscheduler": [
                "pyproject.toml:23",
                "pyproject.toml:49",
                "uv.lock:228"
              ],
              "APScheduler": [
                "pyproject.toml:23",
                "pyproject.toml:49",
                "uv.lock:228"
              ]
            },
            "imported_in_source": {
              "apscheduler": [
                "app/core/scheduler.py:13"
              ],
              "APScheduler": [
                "app/core/scheduler.py:13"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [
            "legacy.runtime.scheduler"
          ],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "legacy.runtime.scheduler",
            "scheduling"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['legacy.runtime.scheduler', 'scheduling'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "legacy.runtime.scheduler",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "scheduling",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C012",
        "name": "APScheduler",
        "version": "uv.lock",
        "canonical_url": "https://github.com/agronholm/apscheduler",
        "capability": "scheduling",
        "code_license": "MIT",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source"
        ],
        "product_path": "Runtime scheduler",
        "evidence": "Scheduling in use",
        "decision": "Retain existing narrow responsibility. Do not expand into workflow-orchestration territory (Temporal/Prefect/Airflow deferred).",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "apscheduler",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "uv.lock",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "archeaxiscoreknowledge",
      "display_names": [
        "ArcheAxis Core Knowledge",
        "Core Knowledge",
        "Canonical knowledge and source lifecycle"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "archeaxiscoreknowledge",
        "display_names": [
          "ArcheAxis Core Knowledge",
          "Core Knowledge",
          "Canonical knowledge and source lifecycle"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "ArcheAxis Core Knowledge",
            "capability_id": "document.save"
          },
          "supply_chain_ledger": null,
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": null
        },
        "verification_tier": "A",
        "currently_usable": true,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": null,
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "Core Knowledge",
            "Canonical knowledge and source lifecycle"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "document.save"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['Core Knowledge', 'Canonical knowledge and source lifecycle'])",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
        "conflicts": [
          {
            "reason": "tier-claims-entry-without-donor-artifact",
            "values": {
              "verification_tier": "A",
              "probed_artifact": "NONE",
              "donor_terms_probed": [
                "Core Knowledge",
                "Canonical knowledge and source lifecycle"
              ],
              "generic_terms_stripped": [],
              "ledger_reported_evidence_state": null
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "document.save",
              "declared_runtime_capabilities_in_the_same_domain": [
                "document.detect"
              ],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": null,
      "qualification": {
        "stable_key": "archeaxiscoreknowledge",
        "disposition": "CURRENT_PAGE_SELECTED",
        "reason": "First-party Core knowledge surfaces retained under their own existing stable keys; CoreDocument is the canonical versioned object contract, not an invented OSS donor or second store.",
        "activation": {
          "state": "CURRENT_PAGE_REFERENCE_ONLY",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "UF10/O01 current page"
        },
        "evidence": {
          "version": {
            "state": "SOURCE_CONTRACT",
            "value": {
              "CoreDocument": "DocumentDto/canonical document create/draft/version",
              "first_party_row": [
                "ArcheAxis Core Knowledge",
                "Core Knowledge",
                "Canonical knowledge and source lifecycle"
              ],
              "independent_donor_version": null
            },
            "source_refs": [
              {
                "path": "crates/archeaxis-domain/src/document.rs",
                "sha256": "1da8a3a3b3035852daf210f45dae5699c0abcce5b721784743fe5f09b9f45ef9"
              },
              {
                "path": "frontend/src/api/generated/core-contract.ts",
                "sha256": "1f6e8e9b69a1258ff0804953f1999a2f46b4fc4d023a5526854e65ea0cf141a1"
              }
            ]
          },
          "license": {
            "state": "FIRST_PARTY_PROJECT_LICENSE",
            "value": {
              "code": "Project LICENSE; third-party dependencies retain independent licenses",
              "weights": "NOT_APPLICABLE"
            },
            "source_refs": [
              {
                "path": "LICENSE",
                "sha256": "b247e647f770f10e281cd662a1b1626461469d056c8b5c65e0c94c87a724f334"
              },
              {
                "path": "Cargo.lock",
                "sha256": "8cb82278834c9c1ec20fc27529810270d1d8157cfbe398c991d223f95e3e849b"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "A",
              "currently_usable": true,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "azulzulucommunityjre21",
      "display_names": [
        "Azul Zulu Community JRE 21 (the runtime the Tika sidecar needs)"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "SIDECAR",
      "classification_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "azulzulucommunityjre21",
        "display_names": [
          "Azul Zulu Community JRE 21 (the runtime the Tika sidecar needs)"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "Azul Zulu Community JRE 21 (the runtime the Tika sidecar needs)",
            "capability_id": "runtime.jvm"
          },
          "supply_chain_ledger": {
            "id": "A050",
            "capability": "document-legacy"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": null
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "SIDECAR",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "SIDECAR",
          "derived_mode": "SIDECAR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "tool_invoked",
          "carried": true,
          "terms": [
            "Azul Zulu Community JRE 21"
          ],
          "hits": {
            "tool_invoked": {
              "Azul Zulu Community JRE 21": [
                "zulu-jre",
                "services/python-workers/document/worker_office.py:740",
                "services/python-workers/tool_paths.py:56"
              ]
            }
          },
          "bound_resource_entries": [
            "zulu-jre"
          ],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "document-legacy",
            "runtime.jvm"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['document-legacy', 'runtime.jvm'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "document-legacy",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "runtime.jvm",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A050",
        "name": "Azul Zulu Community JRE 21 (the runtime the Tika sidecar needs)",
        "version": "Zulu build unknown, JAVA_VERSION 21.0.12.1",
        "canonical_url": "https://cdn.azul.com/zulu/bin/zulu21.52.203-ca-jre21.0.12.1-win_x64.zip",
        "capability": "document-legacy",
        "code_license": "GPL-2.0-or-later with Classpath Exception, read from legal/java.base (LICENSE plus ASSEMBLY_EXCEPTION) inside the distribution",
        "model_license": null,
        "disposition": "SIDECAR",
        "qualification": [
          "installed"
        ],
        "product_path": "services/python-workers/document/worker_office.py",
        "evidence": "Placed under the declared external tool root as `10-toolchains/java/zulu-jre-21.0.12.1/` (50624-byte launcher, sha256 `3dd3b8ca1b9402119060e1085a5aec44b00e600e61944ead36057c4f7f4da29f`) after verifying the download against Azul's own metadata API - package `zulu21.52.203-ca-jre21.0.12.1-win_x64.zip`, 49,264,410 bytes, sha256 `37ad372b04da388c326f0507abec38b8e1d11e3bddf6128b215c8f0a06ff8177`, fetched 2026-10-07. `java -version` exits 0 and self-reports `openjdk version \"21.0.12.1\" 2026-08-18 LTS`; the worker asks that question before handing over a document, so a file that exists but cannot state what it is is refused. Temurin was the first choice and its API publishes the same checksum field, but its download host is unreachable from this machine, so the runtime came from a second publisher whose CDN answers; the record names which, because 'a JVM' is not a supply-chain statement.",
        "decision": "Removable local runtime for the `.ppt` sidecar only. Not bundled, not a system install, not registered anywhere outside the external tool root, and never substituted for another JVM by the product. If Tika is ever dropped, this row goes with it.",
        "upstream_note": "Azul states Zulu Community builds are GPLv2 with the Classpath Exception; the text in this distribution (legal/java.base/LICENSE and ASSEMBLY_EXCEPTION) is what the row relies on rather than that statement alone. The distribution also carries a DISCLAIMER from Azul."
      },
      "qualification": {
        "stable_key": "azulzulucommunityjre21",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "Zulu build unknown, JAVA_VERSION 21.0.12.1",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "GPL-2.0-or-later with Classpath Exception, read from legal/java.base (LICENSE plus ASSEMBLY_EXCEPTION) inside the distribution",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SIDECAR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "installed"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "capcoreknowledge",
      "display_names": [
        "Canonical knowledge and source lifecycle",
        "first-party Rust Core"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "capcoreknowledge",
        "display_names": [
          "Canonical knowledge and source lifecycle",
          "first-party Rust Core"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-CORE-KNOWLEDGE",
            "absorption_mode": "DIRECT_DEPENDENCY",
            "status": "integrated"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-CORE-KNOWLEDGE"
          ]
        },
        "verification_tier": null,
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": "DIRECT_DEPENDENCY",
          "capability_absorption_registry_status": "integrated",
          "supply_chain_ledger": null,
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "tool_invoked",
          "carried": true,
          "terms": [
            "Canonical knowledge and source lifecycle",
            "first-party Rust Core",
            "first_party Rust Core"
          ],
          "hits": {
            "tool_invoked": {
              "first-party Rust Core": [
                "rust",
                "shared/canvas.py:139",
                "shared/file_detection.py:135"
              ],
              "first_party Rust Core": [
                "rust",
                "shared/canvas.py:139",
                "shared/file_detection.py:135"
              ]
            }
          },
          "bound_resource_entries": [
            "rust"
          ],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['(none)'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
        "conflicts": []
      },
      "ledger": null,
      "qualification": {
        "stable_key": "capcoreknowledge",
        "disposition": "CURRENT_PAGE_SELECTED",
        "reason": "First-party Core knowledge surfaces retained under their own existing stable keys; CoreDocument is the canonical versioned object contract, not an invented OSS donor or second store.",
        "activation": {
          "state": "CURRENT_PAGE_REFERENCE_ONLY",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "UF10/O01 current page"
        },
        "evidence": {
          "version": {
            "state": "SOURCE_CONTRACT",
            "value": {
              "CoreDocument": "DocumentDto/canonical document create/draft/version",
              "first_party_row": [
                "Canonical knowledge and source lifecycle",
                "first-party Rust Core"
              ],
              "independent_donor_version": null
            },
            "source_refs": [
              {
                "path": "crates/archeaxis-domain/src/document.rs",
                "sha256": "1da8a3a3b3035852daf210f45dae5699c0abcce5b721784743fe5f09b9f45ef9"
              },
              {
                "path": "frontend/src/api/generated/core-contract.ts",
                "sha256": "1f6e8e9b69a1258ff0804953f1999a2f46b4fc4d023a5526854e65ea0cf141a1"
              }
            ]
          },
          "license": {
            "state": "FIRST_PARTY_PROJECT_LICENSE",
            "value": {
              "code": "Project LICENSE; third-party dependencies retain independent licenses",
              "weights": "NOT_APPLICABLE"
            },
            "source_refs": [
              {
                "path": "LICENSE",
                "sha256": "b247e647f770f10e281cd662a1b1626461469d056c8b5c65e0c94c87a724f334"
              },
              {
                "path": "Cargo.lock",
                "sha256": "8cb82278834c9c1ec20fc27529810270d1d8157cfbe398c991d223f95e3e849b"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": null,
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "chromium",
      "display_names": [
        "Chromium (the Playwright browser build this host already carries)"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "chromium",
        "display_names": [
          "Chromium (the Playwright browser build this host already carries)"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "Chromium (the Playwright browser build this host already carries)",
            "capability_id": "web.snapshot.dynamic"
          },
          "supply_chain_ledger": {
            "id": "A049",
            "capability": "web-render"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": null
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "SIDECAR",
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "Chromium"
          ],
          "hits": {
            "pipeline_invoked": {
              "Chromium": [
                ".github/workflows/ci.yml:677",
                ".github/workflows/nightly.yml:82"
              ]
            },
            "imported_in_source": {
              "Chromium": [
                "services/python-workers/web/worker_webpage.py:302"
              ]
            },
            "tool_invoked": {
              "Chromium": [
                "playwright-chromium",
                "services/python-workers/web/worker_webpage.py:257"
              ]
            },
            "mentioned_only": {
              "Chromium": [
                "services/python-workers/README.md:31",
                "services/python-workers/tool_paths.py:55",
                "app/ingestion/web_screenshot.py:1"
              ]
            }
          },
          "bound_resource_entries": [
            "playwright-chromium"
          ],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "web-render",
            "web.snapshot.dynamic"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['web-render', 'web.snapshot.dynamic'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "web-render",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "web.snapshot.dynamic",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A049",
        "name": "Chromium (the Playwright browser build this host already carries)",
        "version": "build 1228; the launched browser self-reported 149.0.7827.55",
        "canonical_url": "https://playwright.dev/python/docs/browsers",
        "capability": "web-render",
        "code_license": "BSD-3-Clause (Chromium), as recorded by the capability manifest entry",
        "model_license": null,
        "disposition": "SIDECAR",
        "qualification": [
          "installed"
        ],
        "product_path": "services/python-workers/web/worker_webpage.py",
        "evidence": "Used by the F03 render lane, so it is recorded here rather than left as a test-only tool. Measured on this host: `D:/All projects/OS External Configuration/10-toolchains/playwright/chromium-1228/chrome-win64/chrome.exe` 4059648 bytes, sha256 `b798f9e53a98d29eb7f36f8c409f905d3184780a04d2bcb56989067194784bd1`, declared in `config/environment/capability-requirements.yaml` as the `external_paths` of the pre-existing `playwright-chromium` entry, which until now carried a name and no location - the same class of gap as the antiword row: present on disk is not declared, and declared by name is not resolvable. The `playwright` Python package itself is a locked first-party dependency (`playwright>=1.61,<1.62` in `pyproject.toml`), not an added one; this row is about the browser binary the product launches. Resolution order in `services/python-workers/web/worker_webpage.py` is `ARCHEAXIS_CHROMIUM_CMD`, then the declared path, then Playwright's own registry, and a configured path that fails is reported as that failure rather than answered with the declared browser - no substitution. Two host traps shaped the code: a session can redirect `PLAYWRIGHT_BROWSERS_PATH` to a project-local cache that holds no build (which is why the real render test skipped before this row existed), and the declared path carries the build number `chromium-1228`, so a Playwright upgrade invalidates this one entry instead of silently pointing the render at some other browser. Verified through the sanctioned runner with no browser environment variable set: tests/workers/test_webpage_render.py plus the manifest and index workflow tests reported 20 passed / 0 skipped, and the full `tests` suite moved from 4284 passed / 31 skipped to 4286 passed / 30 skipped - the +2 / -1 being the new no-substitution test and the real browser test that the declaration stopped skipping.",
        "decision": "Isolated, removable sidecar for the dynamic-page render lane. Not bundled, not installed by this repository, and not relicensed by it; the repository never assumes the browser exists and a host without it gets a named refusal that writes nothing. Advancing this row's qualification further (an `release`-grade claim) would need a per-page human acceptance on real targets, which this round does not have; screenshots, interaction-gated content and lazy content past the scroll budget remain open in the F03 row.",
        "upstream_note": "Chromium is upstream for the engine; the build measured here was placed on this host by Playwright's own browser download, and the manifest names the same source URL. No copy was made by this repository: the declared path is the build already under `10-toolchains/playwright/`."
      },
      "qualification": {
        "stable_key": "chromium",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "build 1228; the launched browser self-reported 149.0.7827.55",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "BSD-3-Clause (Chromium), as recorded by the capability manifest entry",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "installed"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "cognee",
      "display_names": [
        "Cognee",
        "Graph, memory, and ontology benchmark reference"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "cognee",
        "display_names": [
          "Cognee",
          "Graph, memory, and ontology benchmark reference"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-COGNEE",
            "absorption_mode": "REFERENCE_ONLY",
            "status": "reference"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-COGNEE"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": "REFERENCE_ONLY",
          "capability_absorption_registry_status": "reference",
          "supply_chain_ledger": null,
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "mentioned_only",
          "carried": false,
          "terms": [
            "Cognee",
            "Graph, memory, and ontology benchmark reference"
          ],
          "hits": {
            "mentioned_only": {
              "Cognee": [
                "app/knowledge/graph_pipeline.py:1"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed mentioned_only for terms ['Cognee', 'Graph, memory, and ontology benchmark reference'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
        "conflicts": []
      },
      "ledger": null,
      "qualification": {
        "stable_key": "cognee",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "crawl4ai",
      "display_names": [
        "unclecode/crawl4ai",
        "Crawl4AI"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "crawl4ai",
        "display_names": [
          "unclecode/crawl4ai",
          "Crawl4AI"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "unclecode/crawl4ai",
            "capability_id": "legacy.web.fetch"
          },
          "supply_chain_ledger": {
            "id": "C005",
            "capability": "web-dynamic"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "C005"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "crawl4ai",
            "Crawl4AI"
          ],
          "hits": {
            "package_declared": {
              "crawl4ai": [
                "pyproject.toml:110",
                "uv.lock:890"
              ],
              "Crawl4AI": [
                "pyproject.toml:110",
                "uv.lock:890"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [
            "legacy.web.fetch"
          ],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "legacy.web.fetch",
            "web-dynamic"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['legacy.web.fetch', 'web-dynamic'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "legacy.web.fetch",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "web-dynamic",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C005",
        "name": "Crawl4AI",
        "version": "uv.lock",
        "canonical_url": "https://github.com/unclecode/crawl4ai",
        "capability": "web-dynamic",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source"
        ],
        "product_path": "shared-contracts/adapters/crawlers/crawl4ai_adapter.py",
        "evidence": "Integration test; optional sidecar",
        "decision": "Dynamic page sidecar ONLY. Never a default always-on crawler. SSRF/sandbox/snapshot/prompt-injection gates required before any automated use. Does not grant external content 'truth' identity.",
        "upstream_note": "Apache-2.0."
      },
      "qualification": {
        "stable_key": "crawl4ai",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "uv.lock",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "crawleepython",
      "display_names": [
        "Crawlee Python"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "SIDECAR",
      "classification_reason": "no single atlas capability joins it: capability ids ['web-dynamic-fallback'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "crawleepython",
        "display_names": [
          "Crawlee Python"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "A012",
            "capability": "web-dynamic-fallback"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A012"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "SIDECAR",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "SIDECAR",
          "derived_mode": "SIDECAR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "tool_invoked",
          "carried": true,
          "terms": [
            "Crawlee Python"
          ],
          "hits": {
            "tool_invoked": {
              "Crawlee Python": [
                "python",
                "shared/adapter_contract.py:41",
                "shared/adapter_fixtures.py:380"
              ]
            }
          },
          "bound_resource_entries": [
            "python"
          ],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "web-dynamic-fallback"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['web-dynamic-fallback'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['web-dynamic-fallback'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "disposition-says-adopted-tier-says-not",
            "values": {
              "verification_tier": "D",
              "supply_chain_disposition": "SIDECAR",
              "adoption_artifact": "tool_invoked"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "web-dynamic-fallback",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A012",
        "name": "Crawlee Python",
        "canonical_url": "https://github.com/apify/crawlee-python",
        "capability": "web-dynamic-fallback",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "SIDECAR",
        "qualification": [
          "source"
        ],
        "decision": "Alternative dynamic page sidecar to Crawl4AI. Used only when static extraction is insufficient and user has authorized. Not a default always-on crawler.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "crawleepython",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SIDECAR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "crossrefrest",
      "display_names": [
        "Crossref REST"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "crossrefrest",
        "display_names": [
          "Crossref REST"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "Crossref REST",
            "capability_id": "evidence.crossref"
          },
          "supply_chain_ledger": {
            "id": "A018",
            "capability": "evidence-doi"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A018"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "Crossref REST",
            "crossref"
          ],
          "hits": {
            "imported_in_source": {
              "crossref": [
                "shared/evidence_connectors.py:61",
                "shared/public_evidence.py:13"
              ]
            },
            "mentioned_only": {
              "Crossref REST": [
                "shared/evidence_connectors.py:4"
              ],
              "crossref": [
                "shared/pipeline.py:11"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "evidence-doi",
            "evidence.crossref"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['evidence-doi', 'evidence.crossref'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "evidence-doi",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "evidence.crossref",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A018",
        "name": "Crossref REST",
        "canonical_url": "https://crossref.org/documentation/retrieve-metadata/rest-api/",
        "capability": "evidence-doi",
        "code_license": "public API",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "DOI/author/title/journal metadata. Public/polite pool. Read rate/concurrency headers; 429 backoff.",
        "upstream_note": "API, not a library."
      },
      "qualification": {
        "stable_key": "crossrefrest",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "public API",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "dataciterest",
      "display_names": [
        "DataCite REST"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "dataciterest",
        "display_names": [
          "DataCite REST"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "DataCite REST",
            "capability_id": "evidence.datacite"
          },
          "supply_chain_ledger": {
            "id": "A019",
            "capability": "evidence-dataset-doi"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A019"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "DataCite REST",
            "datacite"
          ],
          "hits": {
            "imported_in_source": {
              "datacite": [
                "shared/evidence_connectors.py:93",
                "shared/public_evidence.py:14"
              ]
            },
            "mentioned_only": {
              "DataCite REST": [
                "shared/evidence_connectors.py:5"
              ],
              "datacite": [
                "shared/pipeline.py:198"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "evidence-dataset-doi",
            "evidence.datacite"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['evidence-dataset-doi', 'evidence.datacite'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "evidence-dataset-doi",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "evidence.datacite",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A019",
        "name": "DataCite REST",
        "canonical_url": "https://support.datacite.org/docs/api",
        "capability": "evidence-dataset-doi",
        "code_license": "public API",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "DataCite DOI and dataset metadata. Open metadata; preserve provenance.",
        "upstream_note": "API, not a library."
      },
      "qualification": {
        "stable_key": "dataciterest",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "public API",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "deeptutor",
      "display_names": [
        "DeepTutor",
        "Source-grounded tutor and recoverable learning workspace"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "SIDECAR",
      "classification_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "deeptutor",
        "display_names": [
          "DeepTutor",
          "Source-grounded tutor and recoverable learning workspace"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "C013",
            "capability": "downstream-learning-product-shell"
          },
          "capability_absorption_registry": {
            "capability_id": "CAP-DEEPTUTOR",
            "absorption_mode": "SIDECAR",
            "status": "candidate"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "C013",
            "CAP-DEEPTUTOR"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "SIDECAR",
        "declared_modes": {
          "capability_absorption_registry": "SIDECAR",
          "capability_absorption_registry_status": "candidate",
          "supply_chain_ledger": "SIDECAR",
          "derived_mode": "SIDECAR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "DeepTutor",
            "Source-grounded tutor and recoverable learning workspace",
            "Source_grounded tutor and recoverable learning workspace",
            "deeptutor"
          ],
          "hits": {
            "pipeline_invoked": {
              "DeepTutor": [
                "scripts/ci/check_deeptutor_notebook.py:1"
              ],
              "deeptutor": [
                "scripts/ci/check_deeptutor_notebook.py:1"
              ]
            },
            "imported_in_source": {
              "DeepTutor": [
                "app/adapters/deeptutor/__init__.py:3",
                "app/adapters/deeptutor/authority.py:48",
                "app/integrations/__init__.py:3"
              ],
              "deeptutor": [
                "app/adapters/deeptutor/__init__.py:3",
                "app/adapters/deeptutor/authority.py:48",
                "app/integrations/__init__.py:3"
              ]
            },
            "mentioned_only": {
              "DeepTutor": [
                "shared/core_client.py:3",
                "app/adapters/deeptutor/custody.py:3",
                "app/learning/capabilities.py:1"
              ],
              "deeptutor": [
                "shared/core_client.py:3",
                "app/adapters/deeptutor/custody.py:3",
                "app/learning/capabilities.py:1"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "downstream-learning-product-shell"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['downstream-learning-product-shell'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
        "conflicts": [
          {
            "reason": "disposition-says-adopted-tier-says-not",
            "values": {
              "verification_tier": "D",
              "supply_chain_disposition": "SIDECAR",
              "adoption_artifact": "imported_in_source"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "downstream-learning-product-shell",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C013",
        "name": "DeepTutor",
        "version": "v1.5.17",
        "canonical_url": "https://github.com/HKUDS/DeepTutor",
        "capability": "downstream-learning-product-shell",
        "code_license": "Apache-2.0",
        "model_license": "provider/model specific; no model weights vendored",
        "disposition": "SIDECAR",
        "qualification": [
          "source",
          "runtime-installed",
          "loopback-http-200",
          "browser-shell-200"
        ],
        "runtime_status": "PARTIAL_MODEL_CONFIGURATION_REQUIRED",
        "archive_sha256": "95f6519174069c73f91bc694cfb9e661e8d8d44239003ba9916b450ee77a4ac3",
        "product_path": "external source/venv body; project data under .hermes/task-runtime/deeptutor-home; authority adapter under app/adapters/deeptutor",
        "upstream_tag_object": "2e522f754c61be7760392151fd22939d570941b8",
        "upstream_commit": "bd80a4d28a2093347ef080f98ae7cf8e3eee488e",
        "tag_signature": "unsigned",
        "decision": "Keep as an optional replaceable learning sidecar behind the authority bridge. The formal product shell is ArcheAxis C#/Avalonia; DeepTutor does not own product navigation. Its KB, memory, users, sessions and indexes are projections only and cannot write Source/Anchor/Claim/Evidence/HumanLearning/MachineCompetence truth.",
        "upstream_note": "Release v1.5.17 published 2026-08-24; Windows fixes included. Golden workflow and restart/rebuild evidence remain required before installed/release qualification."
      },
      "qualification": {
        "stable_key": "deeptutor",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "v1.5.17",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": "provider/model specific; no model weights vendored"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SIDECAR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source",
                "runtime-installed",
                "loopback-http-200",
                "browser-shell-200"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "docling",
      "display_names": [
        "Docling"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "no single atlas capability joins it: capability ids ['document-complex'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "docling",
        "display_names": [
          "Docling"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "A009",
            "capability": "document-complex"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A009"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "EVALUATE",
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "Docling"
          ],
          "hits": {
            "imported_in_source": {
              "Docling": [
                "shared/adapter_fixtures.py:135",
                "app/ingestion/multi_format.py:298"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "document-complex"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['document-complex'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['document-complex'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "declared-non-runtime-but-artifact-is-carried",
            "values": {
              "registry_mode": null,
              "ledger_disposition": "EVALUATE",
              "adoption_artifact": "imported_in_source",
              "hits": {
                "imported_in_source": {
                  "Docling": [
                    "shared/adapter_fixtures.py:135",
                    "app/ingestion/multi_format.py:298"
                  ]
                }
              }
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "document-complex",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A009",
        "name": "Docling",
        "canonical_url": "https://github.com/docling-project/docling",
        "capability": "document-complex",
        "code_license": "MIT",
        "model_license": "per-model SBOM required",
        "disposition": "EVALUATE",
        "qualification": [
          "source"
        ],
        "decision": "Complex document pages only (tables, formulas, multi-column). Code MIT; models licensed independently. Pass model SBOM + Windows qualification before use. NOT a default all-document engine.",
        "upstream_note": "Per-model license audit required."
      },
      "qualification": {
        "stable_key": "docling",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": "per-model SBOM required"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "easyocr",
      "display_names": [
        "EasyOCR"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "SELF_BUILD_GAP",
      "classification_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "easyocr",
        "display_names": [
          "EasyOCR"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "A003",
            "capability": "ocr-alternative"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A003"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "SELF_BUILD_GAP",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "EVALUATE",
          "derived_mode": "SELF_BUILD_GAP"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "stub_only",
          "carried": false,
          "terms": [
            "EasyOCR"
          ],
          "hits": {
            "stub_only": {
              "EasyOCR": [
                "shared/bakeoff_engines.py:91"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "STUB_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "ocr-alternative"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed stub_only for terms ['EasyOCR'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "ocr-alternative",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A003",
        "name": "EasyOCR",
        "canonical_url": "https://github.com/JaidedAI/EasyOCR",
        "capability": "ocr-alternative",
        "code_license": "Apache-2.0",
        "model_license": "per-model record required",
        "disposition": "EVALUATE",
        "qualification": [
          "source"
        ],
        "decision": "Bake-off candidate. Compare against Tesseract/PaddleOCR/RapidOCR on fixed fixtures. Do not select by reputation alone.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "easyocr",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": "per-model record required"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SELF_BUILD_GAP",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "fasterwhisper",
      "display_names": [
        "SYSTRAN/faster-whisper",
        "faster-whisper"
      ],
      "surface_class": "enableable_plugin",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "atlas capability CAP-0020 exists, config/capability-map.v1.json state is worker_backed, and package_declared evidence names the donor itself in the declared route media.transcribe.",
      "declared_runtime_route": "media.transcribe",
      "original_surface": {
        "stable_key": "fasterwhisper",
        "display_names": [
          "SYSTRAN/faster-whisper",
          "faster-whisper"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "SYSTRAN/faster-whisper",
            "capability_id": "media.transcribe"
          },
          "supply_chain_ledger": {
            "id": "A005",
            "capability": "asr-batch"
          },
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0020",
          "atlas_join_candidates": [
            "CAP-0020"
          ],
          "donor_disposition_archive": [
            "A005"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": "CAP-0020",
        "map_state": "worker_backed",
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "faster-whisper",
            "faster_whisper"
          ],
          "hits": {
            "package_declared": {
              "faster-whisper": [
                "pyproject.toml:34",
                "uv.lock:1114",
                "requirements.txt:21"
              ],
              "faster_whisper": [
                "pyproject.toml:34",
                "uv.lock:1114",
                "requirements.txt:21"
              ]
            },
            "tool_invoked": {
              "faster-whisper": [
                "faster-whisper",
                "faster-whisper-base",
                "shared/bakeoff_engines.py:156",
                "services/python-workers/media/worker_transcribe.py:4"
              ],
              "faster_whisper": [
                "faster-whisper",
                "faster-whisper-base",
                "shared/bakeoff_engines.py:156",
                "services/python-workers/media/worker_transcribe.py:4"
              ]
            },
            "mentioned_only": {
              "faster-whisper": [
                "shared/bakeoff_engines.py:156",
                "services/python-workers/media/worker_transcribe.py:4",
                "services/python-workers/README.md:19"
              ],
              "faster_whisper": [
                "shared/bakeoff_engines.py:159",
                "services/python-workers/media/worker_transcribe.py:132",
                "app/ingestion/asr_adapter.py:75"
              ]
            }
          },
          "bound_resource_entries": [
            "faster-whisper",
            "faster-whisper-base",
            "faster-whisper-large-v3-turbo"
          ],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": "media.transcribe",
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "asr-batch"
          ],
          "enableable": true,
          "degrade_reason": null,
          "route_worker_files": [
            "services/python-workers/media/worker_transcribe.py"
          ],
          "named_in_route_worker": true,
          "frontend_only_client": false
        },
        "surface_class": "enableable_plugin",
        "surface_class_reason": "atlas capability CAP-0020 exists, config/capability-map.v1.json state is worker_backed, and package_declared evidence names the donor itself in the declared route media.transcribe.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "asr-batch",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A005",
        "name": "faster-whisper",
        "canonical_url": "https://github.com/SYSTRAN/faster-whisper",
        "capability": "asr-batch",
        "code_license": "MIT",
        "model_license": "MIT (Whisper weights)",
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Primary local ASR candidate. CTranslate2-based, quantized, no API key. Compare WER/RAM/latency against whisper.cpp on fixed Chinese/English corpus.",
        "upstream_note": "Code MIT; Whisper weights MIT. Separate qualification from other ASR candidates."
      },
      "qualification": {
        "stable_key": "fasterwhisper",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": "MIT (Whisper weights)"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": "media.transcribe",
              "enableable_inherited": true,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "ffmpeg",
      "display_names": [
        "FFmpeg/FFmpeg",
        "FFmpeg"
      ],
      "surface_class": "enableable_plugin",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "atlas capability CAP-0020 exists, config/capability-map.v1.json state is worker_backed, and imported_in_source evidence names the donor itself in the declared route media.video.",
      "declared_runtime_route": "media.video",
      "original_surface": {
        "stable_key": "ffmpeg",
        "display_names": [
          "FFmpeg/FFmpeg",
          "FFmpeg"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "FFmpeg/FFmpeg",
            "capability_id": "media.video"
          },
          "supply_chain_ledger": null,
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0020",
          "atlas_join_candidates": [
            "CAP-0020"
          ],
          "donor_disposition_archive": null
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": null,
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": "CAP-0020",
        "map_state": "worker_backed",
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "FFmpeg"
          ],
          "hits": {
            "pipeline_invoked": {
              "FFmpeg": [
                ".github/workflows/ci.yml:192",
                ".github/workflows/nightly.yml:87",
                "scripts/ci/check_vnext_workers.py:243"
              ]
            },
            "imported_in_source": {
              "FFmpeg": [
                "shared/adapter_fixtures.py:36",
                "shared/media_extractor.py:102",
                "services/python-workers/media/window_transcribe.py:27"
              ]
            },
            "tool_invoked": {
              "FFmpeg": [
                "ffmpeg",
                "shared/adapter_contract.py:63",
                "shared/adapter_fixtures.py:36"
              ]
            },
            "stub_only": {
              "FFmpeg": [
                "services/python-workers/media/worker_video.py:64"
              ]
            },
            "mentioned_only": {
              "FFmpeg": [
                "shared/adapter_contract.py:63",
                "services/python-workers/README.md:20",
                "services/python-workers/tool_paths.py:9"
              ]
            }
          },
          "bound_resource_entries": [
            "ffmpeg"
          ],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": "media.video",
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [],
          "enableable": true,
          "degrade_reason": null,
          "route_worker_files": [
            "services/python-workers/media/worker_video.py"
          ],
          "named_in_route_worker": true,
          "frontend_only_client": false
        },
        "surface_class": "enableable_plugin",
        "surface_class_reason": "atlas capability CAP-0020 exists, config/capability-map.v1.json state is worker_backed, and imported_in_source evidence names the donor itself in the declared route media.video.",
        "conflicts": []
      },
      "ledger": null,
      "qualification": {
        "stable_key": "ffmpeg",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": "media.video",
              "enableable_inherited": true,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "firecrawl",
      "display_names": [
        "Firecrawl"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "firecrawl",
        "display_names": [
          "Firecrawl"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "B006",
            "capability": "web-crawler"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "B006"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REVIEW-BLOCK",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "Firecrawl"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "web-crawler"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['Firecrawl'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "web-crawler",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "B006",
        "name": "Firecrawl",
        "canonical_url": "https://github.com/firecrawl/firecrawl",
        "capability": "web-crawler",
        "code_license": "AGPL-3.0 (main); MIT (SDK/UI)",
        "model_license": null,
        "disposition": "REVIEW-BLOCK",
        "decision": "Main service is AGPL-3.0. SDK/UI portions may be MIT — component-level review required. NOT a default embedded dependency. Remote service or AGPL sidecar only.",
        "upstream_note": "AGPL main; some SDK/UI MIT. Do not summarize as one license."
      },
      "qualification": {
        "stable_key": "firecrawl",
        "disposition": "REVIEW-BLOCK",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "AGPL-3.0 (main); MIT (SDK/UI)",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "fsrs",
      "display_names": [
        "open-spaced-repetition/py-fsrs",
        "py-fsrs",
        "fsrs"
      ],
      "surface_class": "enableable_plugin",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "atlas capability CAP-0040 exists, config/capability-map.v1.json state is core_native, and package_declared evidence names the donor itself.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "fsrs",
        "display_names": [
          "open-spaced-repetition/py-fsrs",
          "py-fsrs",
          "fsrs"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "open-spaced-repetition/py-fsrs",
            "capability_id": "learning.fsrs"
          },
          "supply_chain_ledger": {
            "id": "A015",
            "capability": "spaced-repetition"
          },
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0040",
          "atlas_join_candidates": [
            "CAP-0040"
          ],
          "donor_disposition_archive": [
            "A015"
          ]
        },
        "verification_tier": "A",
        "currently_usable": true,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": "CAP-0040",
        "map_state": "core_native",
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "py-fsrs",
            "py_fsrs",
            "fsrs"
          ],
          "hits": {
            "package_declared": {
              "fsrs": [
                "pyproject.toml:37",
                "pyproject.toml:72",
                "uv.lock:1325"
              ]
            },
            "pipeline_invoked": {
              "fsrs": [
                ".github/workflows/vnext-ci.yml:90"
              ]
            },
            "imported_in_source": {
              "fsrs": [
                "shared/learning_scheduler.py:14",
                "services/python-workers/learning/worker_schedule.py:145",
                "app/knowledge/due_queue.py:39"
              ]
            },
            "stub_only": {
              "fsrs": [
                "crates/archeaxis-api/src/lib.rs:635",
                "crates/archeaxis-api/tests/contract_constant_fields.rs:332",
                "crates/archeaxis-api/tests/contract_review_cost.rs:206"
              ]
            },
            "mentioned_only": {
              "fsrs": [
                "shared/core_client.py:61",
                "app/api/learning.py:8",
                "app/contracts/learning_kernel_v1.py:10"
              ],
              "py-fsrs": [
                "shared/learning_scheduler.py:1",
                "services/python-workers/learning/worker_schedule.py:4",
                "app/knowledge/retrieval_practice.py:91"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "learning.fsrs",
            "spaced-repetition"
          ],
          "enableable": true,
          "degrade_reason": null,
          "frontend_only_client": false
        },
        "surface_class": "enableable_plugin",
        "surface_class_reason": "atlas capability CAP-0040 exists, config/capability-map.v1.json state is core_native, and package_declared evidence names the donor itself.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "learning.fsrs",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "spaced-repetition",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A015",
        "name": "py-fsrs",
        "canonical_url": "https://github.com/open-spaced-repetition/py-fsrs",
        "capability": "spaced-repetition",
        "code_license": "MIT",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Existing py-fsrs path remains the single review scheduler; scheduling is not proof of practical mastery. No second learning-state database.",
        "upstream_note": "Task distribution MIT LICENSE SHA256 021bff58ad2685d7e5b30d307429bc7cfdca108ad620ce889abb38d7acd89ace. Installed desktop/release qualification NOT_RUN.",
        "history": [
          {
            "recorded_at": "2026-10-08",
            "reason": "Current source/result correction; original claim retained, not deleted.",
            "original_record": {
              "id": "A015",
              "name": "py-fsrs",
              "canonical_url": "https://github.com/open-spaced-repetition/py-fsrs",
              "capability": "spaced-repetition",
              "code_license": "MIT",
              "model_license": null,
              "disposition": "ADOPT",
              "qualification": [
                "source"
              ],
              "decision": "Interval/scheduling for learning cards. Each card must point back to an EvidenceAnchor. H4 target.",
              "upstream_note": null
            }
          }
        ],
        "version": "6.3.2 (uv.lock and task environment metadata)",
        "evidence": "Rust scheduler -> services/python-workers/learning/worker_schedule.py -> shared/learning_scheduler.py independent of routes.json. Core learning_state_api and learning_events_api pass save/reopen and retry deduplication tests on 2026-10-08.",
        "current_task_verification": "docs/current/OSS-REUSE-VERIFICATION-20261008.json"
      },
      "qualification": {
        "stable_key": "fsrs",
        "disposition": "CURRENT_PAGE_SELECTED",
        "reason": "Only this page needs the existing surface; qualification remains separated from runtime availability.",
        "activation": {
          "state": "CURRENT_PAGE_REFERENCE_ONLY",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "UF10/O01 current page"
        },
        "evidence": {
          "version": {
            "state": "LOCK_PINNED",
            "value": {
              "package": "fsrs",
              "version": "6.3.2",
              "source": {
                "registry": "https://pypi.org/simple"
              },
              "pyproject_range_is_not_version": true
            },
            "source_refs": [
              {
                "path": "uv.lock",
                "sha256": "0e3db03c3dcd71e24acc13022839591b575f10e42f1dbdfde8b86ec77fc8f2e3"
              },
              {
                "path": "pyproject.toml",
                "sha256": "8df2995c350abea2dcb4d8b6f13e80c165abe9d7b2f5ca7d503ace3a6006a63c"
              }
            ]
          },
          "license": {
            "state": "LOCAL_DECLARATION_WITH_OFFICIAL_READBACK",
            "value": {
              "code": "MIT",
              "weights": "NOT_APPLICABLE",
              "prior_license_file_sha256": "021bff58ad2685d7e5b30d307429bc7cfdca108ad620ce889abb38d7acd89ace",
              "official_sources": [
                "https://github.com/open-spaced-repetition/py-fsrs/blob/main/LICENSE"
              ],
              "official_head_is_not_locked_license_hash": true
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-REUSE-VERIFICATION-20261008.json",
                "sha256": "67c25efebac6d42ab4a20e82c27b4f771acaffeafff0a5d913cab38b45ae2cf0"
              },
              {
                "path": "uv.lock",
                "sha256": "0e3db03c3dcd71e24acc13022839591b575f10e42f1dbdfde8b86ec77fc8f2e3"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": true,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED",
              "local_saved_input_only": true,
              "knowledge_writer": "Core only",
              "no_new_network_fetch": true
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "A",
              "currently_usable": true,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "funasr",
      "display_names": [
        "FunASR / SenseVoice"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "funasr",
        "display_names": [
          "FunASR / SenseVoice"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "B004",
            "capability": "asr-chinese"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "B004"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REVIEW-BLOCK",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "mentioned_only",
          "carried": false,
          "terms": [
            "FunASR",
            "SenseVoice"
          ],
          "hits": {
            "mentioned_only": {
              "SenseVoice": [
                "services/python-workers/README.md:47",
                "app/ingestion/asr_adapter.py:95"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "asr-chinese"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed mentioned_only for terms ['FunASR', 'SenseVoice'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "asr-chinese",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "B004",
        "name": "FunASR / SenseVoice",
        "canonical_url": "https://github.com/modelscope/FunASR",
        "capability": "asr-chinese",
        "code_license": "MIT",
        "model_license": "custom-modifiable",
        "disposition": "REVIEW-BLOCK",
        "decision": "Code MIT. MODEL license has behavioral clauses, auto-revision terms, and undefined jurisdiction. Not a default component. Review per specific model.",
        "upstream_note": "Separate code vs model license — model terms are the blocker."
      },
      "qualification": {
        "stable_key": "funasr",
        "disposition": "REVIEW-BLOCK",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": "custom-modifiable"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "gitleaks",
      "display_names": [
        "Gitleaks"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "SIDECAR",
      "classification_reason": "no single atlas capability joins it: capability ids ['secret-scan'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "gitleaks",
        "display_names": [
          "Gitleaks"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "A024",
            "capability": "secret-scan"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A024"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "SIDECAR",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "SIDECAR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "pipeline_invoked",
          "carried": true,
          "terms": [
            "Gitleaks",
            "gitleaks"
          ],
          "hits": {
            "pipeline_invoked": {
              "Gitleaks": [
                ".github/workflows/ci.yml:172"
              ],
              "gitleaks": [
                ".github/workflows/ci.yml:172"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "secret-scan"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['secret-scan'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['secret-scan'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "disposition-says-adopted-tier-says-not",
            "values": {
              "verification_tier": "D",
              "supply_chain_disposition": "ADOPT",
              "adoption_artifact": "pipeline_invoked"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "secret-scan",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A024",
        "name": "Gitleaks",
        "canonical_url": "https://github.com/gitleaks/gitleaks",
        "capability": "secret-scan",
        "code_license": "MIT",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Secret scanning. CI/release tool. NOT packaged into product. Enforcing since 2026-10-06.",
        "upstream_note": "Local admission probe 2026-10-06: upstream checksums verified the downloaded asset (windows_x64 sha256 d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e; packaged LICENSE 1069 bytes, sha256 e3884b252b3bfc045e55be43a34d1e80da070bc6f804ac95bf4660e97d62ebc6). gitleaks 8.30.1 detected a planted AWS access key and GitHub PAT in a fixture and reported nothing else; detect over the 2480-commit history and the tracked checkout is clean under .gitleaks.toml.",
        "adopted_revision": "8.30.1",
        "adopted_kind": "CI tool (release asset verified by sha256 before use)",
        "adopted_asset": "gitleaks_8.30.1_linux_x64.tar.gz",
        "adopted_asset_sha256": "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
        "adopted_wired_at": ".github/workflows/ci.yml test job; enforcing since 2026-10-06 - continue-on-error removed after a clean run, scan runs with --config .gitleaks.toml"
      },
      "qualification": {
        "stable_key": "gitleaks",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SIDECAR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "graphiti",
      "display_names": [
        "Graphiti",
        "Temporal knowledge projection and supersession"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "ALGORITHM_DONOR",
      "classification_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "graphiti",
        "display_names": [
          "Graphiti",
          "Temporal knowledge projection and supersession"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-GRAPHITI",
            "absorption_mode": "ALGORITHM_DONOR",
            "status": "candidate"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-GRAPHITI"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "ALGORITHM_DONOR",
        "declared_modes": {
          "capability_absorption_registry": "ALGORITHM_DONOR",
          "capability_absorption_registry_status": "candidate",
          "supply_chain_ledger": null,
          "derived_mode": "ALGORITHM_DONOR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "mentioned_only",
          "carried": false,
          "terms": [
            "Graphiti",
            "Temporal knowledge projection and supersession"
          ],
          "hits": {
            "mentioned_only": {
              "Graphiti": [
                "app/memory/temporal_graph.py:1"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed mentioned_only for terms ['Graphiti', 'Temporal knowledge projection and supersession'])",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
        "conflicts": []
      },
      "ledger": null,
      "qualification": {
        "stable_key": "graphiti",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "ALGORITHM_DONOR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "h5pphplibrary",
      "display_names": [
        "H5P PHP Library"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "h5pphplibrary",
        "display_names": [
          "H5P PHP Library"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "B007",
            "capability": "interactive-content"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "B007"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REVIEW-BLOCK",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "H5P PHP Library"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "interactive-content"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['H5P PHP Library'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "interactive-content",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "B007",
        "name": "H5P PHP Library",
        "canonical_url": "https://github.com/h5p/h5p-php-library",
        "capability": "interactive-content",
        "code_license": "GPL-3.0",
        "model_license": null,
        "disposition": "REVIEW-BLOCK",
        "decision": "GPL-3.0 (due to HTML Purifier dependency). Old 'core MIT' conclusion is WRONG. Content types licensed individually. Copyleft sidecar or content exchange only.",
        "upstream_note": "Corrects historical MIT assumption."
      },
      "qualification": {
        "stable_key": "h5pphplibrary",
        "disposition": "REVIEW-BLOCK",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "GPL-3.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "jiwer",
      "display_names": [
        "jitsi/jiwer",
        "JiWER"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "jiwer",
        "display_names": [
          "jitsi/jiwer",
          "JiWER"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "jitsi/jiwer",
            "capability_id": "quality.text"
          },
          "supply_chain_ledger": {
            "id": "A013",
            "capability": "cer-wer-metric"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A013"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "jiwer",
            "JiWER"
          ],
          "hits": {
            "package_declared": {
              "jiwer": [
                "pyproject.toml:35",
                "pyproject.toml:70",
                "uv.lock:1799"
              ],
              "JiWER": [
                "pyproject.toml:35",
                "pyproject.toml:70",
                "uv.lock:1799"
              ]
            },
            "imported_in_source": {
              "jiwer": [
                "shared/text_quality.py:11"
              ],
              "JiWER": [
                "shared/text_quality.py:11"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "cer-wer-metric",
            "quality.text"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['cer-wer-metric', 'quality.text'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "cer-wer-metric",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "quality.text",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A013",
        "name": "JiWER",
        "canonical_url": "https://github.com/jitsi/jiwer",
        "capability": "cer-wer-metric",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Transparent CER/WER computation. ONLY compute when truth/prediction pairs exist. Never report CER/WER from engine confidence alone.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "jiwer",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "jsoncanvas",
      "display_names": [
        "JSON Canvas"
      ],
      "surface_class": "format_spec",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier C is defined as an extracted behaviour/format/test with no runtime adoption implied; the carried reference is a format or protocol contract.",
      "declared_runtime_route": "canvas.structure",
      "original_surface": {
        "stable_key": "jsoncanvas",
        "display_names": [
          "JSON Canvas"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "JSON Canvas",
            "capability_id": "canvas.structure"
          },
          "supply_chain_ledger": {
            "id": "A016",
            "capability": "canvas-file-format"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [
            "CAP-0020",
            "CAP-0100",
            "CAP-0160"
          ],
          "donor_disposition_archive": [
            "A016"
          ]
        },
        "verification_tier": "C",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "mentioned_only",
          "carried": false,
          "terms": [
            "JSON Canvas"
          ],
          "hits": {
            "mentioned_only": {
              "JSON Canvas": [
                "shared/compat/c3.py:1",
                "shared/compat/models.py:5",
                "shared/json_canvas.py:1"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": "canvas.structure",
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "canvas-file-format"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed mentioned_only for terms ['JSON Canvas'])",
          "frontend_only_client": false
        },
        "surface_class": "format_spec",
        "surface_class_reason": "tier C is defined as an extracted behaviour/format/test with no runtime adoption implied; the carried reference is a format or protocol contract.",
        "conflicts": [
          {
            "reason": "atlas-join-ambiguous",
            "values": {
              "atlas_capability_ids": [
                "CAP-0020",
                "CAP-0100",
                "CAP-0160"
              ],
              "note": "more than one atlas capability names this donor or owns its runtime capability; no winner is picked, so the entry cannot claim the plugin class"
            }
          },
          {
            "reason": "claimed-runtime-adoption-without-donor-artifact",
            "values": {
              "registry_mode": null,
              "registry_status": null,
              "ledger_disposition": "ADOPT",
              "verification_tier": "C",
              "probed_artifact": "mentioned_only",
              "donor_terms_probed": [
                "JSON Canvas"
              ],
              "ledger_reported_evidence_state": "DECLARED"
            }
          },
          {
            "reason": "donor-disposition-check-credits-a-generic-term",
            "values": {
              "evidence_state_from_donor_check": "DECLARED",
              "donor_specific_artifact": "mentioned_only",
              "donor_terms_probed": [
                "JSON Canvas"
              ],
              "generic_terms_stripped": [
                "canvas",
                "cff",
                "file",
                "format"
              ],
              "note": "the disposition check probes the row's curated terms, which include the capability's own name; crediting this donor on those hits is the failure mode this crosswalk exists to refuse"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "canvas-file-format",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A016",
        "name": "JSON Canvas",
        "canonical_url": "https://github.com/obsidianmd/jsoncanvas",
        "capability": "canvas-file-format",
        "code_license": "MIT",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Open file format, not a library dependency. Unknown fields preserved on roundtrip. H3 target.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "jsoncanvas",
        "disposition": "CURRENT_PAGE_SELECTED",
        "reason": "Only this page needs the existing surface; qualification remains separated from runtime availability.",
        "activation": {
          "state": "CURRENT_PAGE_REFERENCE_ONLY",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "UF10/O01 current page"
        },
        "evidence": {
          "version": {
            "state": "FORMAT_REFERENCE",
            "value": {
              "format": "JSON Canvas 1.0",
              "implementation": null
            },
            "source_refs": [
              {
                "path": "shared/json_canvas.py",
                "sha256": "a9e2fc1881cca1b54d8086e5d94968d793d5f9b689477804ddfba678f519f9c8"
              }
            ]
          },
          "license": {
            "state": "OFFICIAL_READBACK_NOT_EXACT_SNAPSHOT",
            "value": {
              "code": "MIT",
              "weights": "NOT_APPLICABLE",
              "official_sources": [
                "https://github.com/obsidianmd/jsoncanvas/blob/main/LICENSE"
              ],
              "implementation_license_separate": true
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": "canvas.structure",
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "NOT_APPLICABLE",
              "format_spec_not_plugin": true,
              "external_format_unknown_fields": "Preserve when roundtripping"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "C",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "jsonschemaspec",
      "display_names": [
        "json-schema-org/json-schema-spec"
      ],
      "surface_class": "format_spec",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier C is defined as an extracted behaviour/format/test with no runtime adoption implied; the carried reference is a format or protocol contract.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "jsonschemaspec",
        "display_names": [
          "json-schema-org/json-schema-spec"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "json-schema-org/json-schema-spec",
            "capability_id": "contract.json-schema"
          },
          "supply_chain_ledger": null,
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": null
        },
        "verification_tier": "C",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": null,
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "json-schema-spec",
            "json_schema_spec"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "contract.json-schema"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['json-schema-spec', 'json_schema_spec'])",
          "frontend_only_client": false
        },
        "surface_class": "format_spec",
        "surface_class_reason": "tier C is defined as an extracted behaviour/format/test with no runtime adoption implied; the carried reference is a format or protocol contract.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "contract.json-schema",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": null,
      "qualification": {
        "stable_key": "jsonschemaspec",
        "disposition": "CURRENT_PAGE_SELECTED",
        "reason": "Only this page needs the existing surface; qualification remains separated from runtime availability.",
        "activation": {
          "state": "CURRENT_PAGE_REFERENCE_ONLY",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "UF10/O01 current page"
        },
        "evidence": {
          "version": {
            "state": "FORMAT_REFERENCE",
            "value": {
              "format": "JSON Schema draft 2020-12",
              "implementation": null,
              "python_validator": {
                "package": "jsonschema",
                "version": "4.26.0",
                "source": {
                  "registry": "https://pypi.org/simple"
                },
                "distinct_from_spec_repository": true
              }
            },
            "source_refs": [
              {
                "path": "packages/contracts/v2/expression.schema.json",
                "sha256": "a694b9f269dd61d143c3950172e6d3957914a5caef1d01ffc16f8ce99b09563e"
              },
              {
                "path": "uv.lock",
                "sha256": "0e3db03c3dcd71e24acc13022839591b575f10e42f1dbdfde8b86ec77fc8f2e3"
              }
            ]
          },
          "license": {
            "state": "OFFICIAL_READBACK_NOT_EXACT_SNAPSHOT",
            "value": {
              "code": "Specification repository includes separate BSD-style specification text and AFL-3.0 license terms; not a blanket implementation license",
              "weights": "NOT_APPLICABLE",
              "official_sources": [
                "https://github.com/json-schema-org/json-schema-spec/blob/main/LICENSE"
              ],
              "implementation_license_separate": true
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "NOT_APPLICABLE",
              "format_spec_not_plugin": true,
              "external_format_unknown_fields": "Preserve when roundtripping"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "C",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "kuzu",
      "display_names": [
        "kuzudb/kuzu",
        "Kùzu"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier E or disposition REJECT-CORE: not adopted for the stated role, with the recorded alternative kept in the source row.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "kuzu",
        "display_names": [
          "kuzudb/kuzu",
          "Kùzu"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "kuzudb/kuzu",
            "capability_id": "graph.core-replacement"
          },
          "supply_chain_ledger": {
            "id": "X001_ARCHIVED",
            "capability": "graph-database"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "X001_ARCHIVED"
          ]
        },
        "verification_tier": "E",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REJECT-CORE",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "kuzu"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "graph-database",
            "graph.core-replacement"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['kuzu'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REJECT-CORE: not adopted for the stated role, with the recorded alternative kept in the source row.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "graph-database",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "graph.core-replacement",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "X001_ARCHIVED",
        "name": "Kùzu",
        "canonical_url": "https://github.com/kuzudb/kuzu",
        "capability": "graph-database",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "REJECT-CORE",
        "decision": "Upstream archived 2025-10-10 (read-only). Must not be selected as primary graph component. Remove from active candidate list.",
        "upstream_note": "ARCHIVED."
      },
      "qualification": {
        "stable_key": "kuzu",
        "disposition": "REJECT-CORE",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "E",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "langfuse",
      "display_names": [
        "langfuse/langfuse",
        "Langfuse"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "langfuse",
        "display_names": [
          "langfuse/langfuse",
          "Langfuse"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "langfuse/langfuse",
            "capability_id": "legacy.observability"
          },
          "supply_chain_ledger": {
            "id": "C007",
            "capability": "observability"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "C007"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "langfuse",
            "Langfuse"
          ],
          "hits": {
            "package_declared": {
              "langfuse": [
                "pyproject.toml:111",
                "uv.lock:1860"
              ],
              "Langfuse": [
                "pyproject.toml:111",
                "uv.lock:1860"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [
            "legacy.observability"
          ],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "legacy.observability",
            "observability"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['legacy.observability', 'observability'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "legacy.observability",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "observability",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C007",
        "name": "Langfuse",
        "version": "uv.lock",
        "canonical_url": "https://github.com/langfuse/langfuse",
        "capability": "observability",
        "code_license": "MIT (core)",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source"
        ],
        "product_path": "shared-contracts/adapters/observability/langfuse_adapter.py",
        "evidence": "Adapter test; local fallback",
        "decision": "Payload-safe local fallback required. EE/ directory is separately licensed. Redact secrets and PII before any trace export.",
        "upstream_note": "Core MIT; ee/ dir separately licensed. NOT overall MIT."
      },
      "qualification": {
        "stable_key": "langfuse",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "uv.lock",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT (core)",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "learningmap",
      "display_names": [
        "LearningMAP",
        "Knowledge components, prerequisites, diagnosis, and pedagogy"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "ALGORITHM_DONOR",
      "classification_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "learningmap",
        "display_names": [
          "LearningMAP",
          "Knowledge components, prerequisites, diagnosis, and pedagogy"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-LEARNINGMAP",
            "absorption_mode": "ALGORITHM_DONOR",
            "status": "candidate"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-LEARNINGMAP"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "ALGORITHM_DONOR",
        "declared_modes": {
          "capability_absorption_registry": "ALGORITHM_DONOR",
          "capability_absorption_registry_status": "candidate",
          "supply_chain_ledger": null,
          "derived_mode": "ALGORITHM_DONOR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "LearningMAP"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['LearningMAP'])",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
        "conflicts": []
      },
      "ledger": null,
      "qualification": {
        "stable_key": "learningmap",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "ALGORITHM_DONOR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "lightrag",
      "display_names": [
        "LightRAG",
        "Mixed vector and graph retrieval projection"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "ALGORITHM_DONOR",
      "classification_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "lightrag",
        "display_names": [
          "LightRAG",
          "Mixed vector and graph retrieval projection"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-LIGHTRAG",
            "absorption_mode": "ALGORITHM_DONOR",
            "status": "candidate"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-LIGHTRAG"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "ALGORITHM_DONOR",
        "declared_modes": {
          "capability_absorption_registry": "ALGORITHM_DONOR",
          "capability_absorption_registry_status": "candidate",
          "supply_chain_ledger": null,
          "derived_mode": "ALGORITHM_DONOR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "LightRAG",
            "Mixed vector and graph retrieval projection"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['LightRAG', 'Mixed vector and graph retrieval projection'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
        "conflicts": []
      },
      "ledger": null,
      "qualification": {
        "stable_key": "lightrag",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "ALGORITHM_DONOR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "litellm",
      "display_names": [
        "BerriAI/litellm",
        "LiteLLM"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "litellm",
        "display_names": [
          "BerriAI/litellm",
          "LiteLLM"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "BerriAI/litellm",
            "capability_id": "legacy.llm.gateway"
          },
          "supply_chain_ledger": {
            "id": "C006",
            "capability": "llm-provider-router"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [
            "CAP-0050",
            "CAP-0150"
          ],
          "donor_disposition_archive": [
            "C006"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "litellm",
            "LiteLLM"
          ],
          "hits": {
            "package_declared": {
              "litellm": [
                "pyproject.toml:31",
                "uv.lock:1963",
                "requirements.txt:18"
              ],
              "LiteLLM": [
                "pyproject.toml:31",
                "uv.lock:1963",
                "requirements.txt:18"
              ]
            },
            "imported_in_source": {
              "litellm": [
                "app/knowledge/teach_back_eval.py:171",
                "app/rag/embedder.py:73"
              ],
              "LiteLLM": [
                "app/knowledge/teach_back_eval.py:171",
                "app/rag/embedder.py:73"
              ]
            },
            "mentioned_only": {
              "litellm": [
                "services/python-workers/machine/document_check.py:43",
                "app/memory/reasoning_memory.py:11"
              ],
              "LiteLLM": [
                "services/python-workers/machine/document_check.py:43",
                "app/memory/reasoning_memory.py:11"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [
            "legacy.llm.gateway"
          ],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "legacy.llm.gateway",
            "llm-provider-router"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['legacy.llm.gateway', 'llm-provider-router'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "atlas-join-ambiguous",
            "values": {
              "atlas_capability_ids": [
                "CAP-0050",
                "CAP-0150"
              ],
              "note": "more than one atlas capability names this donor or owns its runtime capability; no winner is picked, so the entry cannot claim the plugin class"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "legacy.llm.gateway",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "llm-provider-router",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C006",
        "name": "LiteLLM",
        "version": "uv.lock",
        "canonical_url": "https://github.com/BerriAI/litellm",
        "capability": "llm-provider-router",
        "code_license": "MIT (core)",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source"
        ],
        "product_path": "shared-contracts/adapters/llm/litellm_adapter.py",
        "evidence": "Integration test",
        "decision": "Thin provider adapter only. Core MIT; enterprise/ directory is separately licensed. Must not own business objects, data model, or auth state. Replaceable.",
        "upstream_note": "Default branch != stable release; lock to exact release tag. Enterprise dir is NOT MIT."
      },
      "qualification": {
        "stable_key": "litellm",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "uv.lock",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT (core)",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "loguru",
      "display_names": [
        "Delgan/loguru",
        "Loguru"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "loguru",
        "display_names": [
          "Delgan/loguru",
          "Loguru"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "Delgan/loguru",
            "capability_id": "runtime.logging"
          },
          "supply_chain_ledger": {
            "id": "C010",
            "capability": "logging"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "C010"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "loguru",
            "Loguru"
          ],
          "hits": {
            "package_declared": {
              "loguru": [
                "pyproject.toml:25",
                "pyproject.toml:56",
                "uv.lock:1986"
              ],
              "Loguru": [
                "pyproject.toml:25",
                "pyproject.toml:56",
                "uv.lock:1986"
              ]
            },
            "imported_in_source": {
              "loguru": [
                "app/ingestion/multi_format.py:746"
              ],
              "Loguru": [
                "app/ingestion/multi_format.py:746"
              ]
            },
            "stub_only": {
              "loguru": [
                "shared/logging.py:18"
              ],
              "Loguru": [
                "shared/logging.py:18"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "logging",
            "runtime.logging"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['logging', 'runtime.logging'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "logging",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "runtime.logging",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C010",
        "name": "Loguru",
        "version": "uv.lock",
        "canonical_url": "https://github.com/Delgan/loguru",
        "capability": "logging",
        "code_license": "MIT",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source",
          "installed"
        ],
        "product_path": "shared/logging.py; app/ingestion/multi_format.py",
        "evidence": "Log paths active",
        "decision": "Retain. Logs must never contain secret plaintext, credentials, internal absolute paths. Converge with structlog to avoid dual-framework duplication.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "loguru",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "uv.lock",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source",
                "installed"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "magika",
      "display_names": [
        "google/magika",
        "Magika"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "CAP-0020 is worker_backed but the entry names no declared route in services/python-workers/routes.json (named ['file-type-routing', 'file.detect'])",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "magika",
        "display_names": [
          "google/magika",
          "Magika"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "google/magika",
            "capability_id": "file.detect"
          },
          "supply_chain_ledger": {
            "id": "A001",
            "capability": "file-type-routing"
          },
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0020",
          "atlas_join_candidates": [
            "CAP-0020"
          ],
          "donor_disposition_archive": [
            "A001"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "EVALUATE",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": "CAP-0020",
        "map_state": "worker_backed",
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "magika",
            "Magika"
          ],
          "hits": {
            "package_declared": {
              "magika": [
                "uv.lock:2118"
              ],
              "Magika": [
                "uv.lock:2118"
              ]
            },
            "vendored": {
              "magika": [
                "shared/models/magika"
              ],
              "Magika": [
                "shared/models/magika"
              ]
            },
            "imported_in_source": {
              "magika": [
                "frontend/src/__tests__/ContentDetectionPanel.test.tsx:14"
              ],
              "Magika": [
                "frontend/src/__tests__/ContentDetectionPanel.test.tsx:14"
              ]
            },
            "stub_only": {
              "magika": [
                "services/python-workers/document/worker_detect.py:70"
              ],
              "Magika": [
                "services/python-workers/document/worker_detect.py:70"
              ]
            },
            "mentioned_only": {
              "magika": [
                "shared/file_detection.py:1",
                "app/ingestion/multi_format.py:91",
                "crates/archeaxis-application/src/attempts.rs:33"
              ],
              "Magika": [
                "shared/file_detection.py:1",
                "app/ingestion/multi_format.py:91",
                "crates/archeaxis-application/src/attempts.rs:33"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "DECLARED_AND_VENDORED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "file-type-routing",
            "file.detect"
          ],
          "enableable": false,
          "degrade_reason": "CAP-0020 is worker_backed but the entry names no declared route in services/python-workers/routes.json (named ['file-type-routing', 'file.detect'])",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "CAP-0020 is worker_backed but the entry names no declared route in services/python-workers/routes.json (named ['file-type-routing', 'file.detect'])",
        "conflicts": [
          {
            "reason": "tier-says-implemented-disposition-says-not",
            "values": {
              "verification_tier": "B",
              "supply_chain_disposition": "EVALUATE",
              "adoption_artifact": "package_declared",
              "source": "docs/current/OSS-REUSE-DECISIONS-20261008.json vs docs/truth/SUPPLY_CHAIN_LEDGER.json"
            }
          },
          {
            "reason": "declared-non-runtime-but-artifact-is-carried",
            "values": {
              "registry_mode": null,
              "ledger_disposition": "EVALUATE",
              "adoption_artifact": "package_declared",
              "hits": {
                "package_declared": {
                  "magika": [
                    "uv.lock:2118"
                  ],
                  "Magika": [
                    "uv.lock:2118"
                  ]
                },
                "vendored": {
                  "magika": [
                    "shared/models/magika"
                  ],
                  "Magika": [
                    "shared/models/magika"
                  ]
                },
                "imported_in_source": {
                  "magika": [
                    "frontend/src/__tests__/ContentDetectionPanel.test.tsx:14"
                  ],
                  "Magika": [
                    "frontend/src/__tests__/ContentDetectionPanel.test.tsx:14"
                  ]
                },
                "stub_only": {
                  "magika": [
                    "services/python-workers/document/worker_detect.py:70"
                  ],
                  "Magika": [
                    "services/python-workers/document/worker_detect.py:70"
                  ]
                },
                "mentioned_only": {
                  "magika": [
                    "shared/file_detection.py:1",
                    "app/ingestion/multi_format.py:91",
                    "crates/archeaxis-application/src/attempts.rs:33"
                  ],
                  "Magika": [
                    "shared/file_detection.py:1",
                    "app/ingestion/multi_format.py:91",
                    "crates/archeaxis-application/src/attempts.rs:33"
                  ]
                }
              }
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "file-type-routing",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "file.detect",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A001",
        "name": "Magika",
        "canonical_url": "https://github.com/google/magika",
        "capability": "file-type-routing",
        "code_license": "Apache-2.0",
        "model_license": "built-in model Apache-2.0",
        "disposition": "EVALUATE",
        "qualification": [
          "source"
        ],
        "decision": "Route-only; not a security proof. Small local model, 200+ types. Bake-off against existing stdlib/libmagic.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "magika",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": "built-in model Apache-2.0"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "marker",
      "display_names": [
        "Marker"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row (a donor artifact exists on this host, which does not lift the gate).",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "marker",
        "display_names": [
          "Marker"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "B003",
            "capability": "pdf-conversion"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "B003"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REVIEW-BLOCK",
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "Marker"
          ],
          "hits": {
            "pipeline_invoked": {
              "Marker": [
                ".github/workflows/ci.yml:51"
              ]
            },
            "imported_in_source": {
              "Marker": [
                "shared/evaluation_fallback.py:145",
                "services/python-workers/web/worker_html.py:36",
                "app/ingestion/multi_format.py:283"
              ]
            },
            "stub_only": {
              "Marker": [
                "services/python-workers/media/worker_transcribe.py:123",
                "services/python-workers/media/worker_video.py:132",
                "frontend/src/__tests__/StatusBar.test.tsx:27"
              ]
            },
            "mentioned_only": {
              "Marker": [
                "services/python-workers/vision/worker_caption.py:67",
                "app/ingestion/raw_asset.py:187",
                "app/setup/setup_status.py:37"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "pdf-conversion"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['pdf-conversion'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row (a donor artifact exists on this host, which does not lift the gate).",
        "conflicts": [
          {
            "reason": "declared-non-runtime-but-artifact-is-carried",
            "values": {
              "registry_mode": null,
              "ledger_disposition": "REVIEW-BLOCK",
              "adoption_artifact": "imported_in_source",
              "hits": {
                "pipeline_invoked": {
                  "Marker": [
                    ".github/workflows/ci.yml:51"
                  ]
                },
                "imported_in_source": {
                  "Marker": [
                    "shared/evaluation_fallback.py:145",
                    "services/python-workers/web/worker_html.py:36",
                    "app/ingestion/multi_format.py:283"
                  ]
                },
                "stub_only": {
                  "Marker": [
                    "services/python-workers/media/worker_transcribe.py:123",
                    "services/python-workers/media/worker_video.py:132",
                    "frontend/src/__tests__/StatusBar.test.tsx:27"
                  ]
                },
                "mentioned_only": {
                  "Marker": [
                    "services/python-workers/vision/worker_caption.py:67",
                    "app/ingestion/raw_asset.py:187",
                    "app/setup/setup_status.py:37"
                  ]
                }
              }
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "pdf-conversion",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "B003",
        "name": "Marker",
        "canonical_url": "https://github.com/datalab-to/marker",
        "capability": "pdf-conversion",
        "code_license": "Apache-2.0 (code)",
        "model_license": "modified OpenRAIL-M (weights)",
        "disposition": "REVIEW-BLOCK",
        "decision": "CODE is Apache-2.0 (CORRECTED from old GPL-3.0 conclusion). WEIGHTS are modified OpenRAIL-M — separate review required. Do not select as default. Corrects historical 'code GPL' error.",
        "upstream_note": "code/weight license split; old GPL-3.0 record is WRONG."
      },
      "qualification": {
        "stable_key": "marker",
        "disposition": "REVIEW-BLOCK",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0 (code)",
              "weights": "modified OpenRAIL-M (weights)"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "markitdown",
      "display_names": [
        "microsoft/markitdown",
        "MarkItDown[pdf]",
        "MarkItDown"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "no single atlas capability joins it: capability ids ['document-conversion', 'legacy.document.convert'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "markitdown",
        "display_names": [
          "microsoft/markitdown",
          "MarkItDown[pdf]",
          "MarkItDown"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "microsoft/markitdown",
            "capability_id": "legacy.document.convert"
          },
          "supply_chain_ledger": {
            "id": "C002",
            "capability": "document-conversion"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [
            "CAP-0020",
            "CAP-0100"
          ],
          "donor_disposition_archive": [
            "C002"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "markitdown",
            "MarkItDown"
          ],
          "hits": {
            "package_declared": {
              "markitdown": [
                "pyproject.toml:27",
                "pyproject.toml:78",
                "uv.lock:2174"
              ],
              "MarkItDown": [
                "pyproject.toml:27",
                "pyproject.toml:78",
                "uv.lock:2174"
              ]
            },
            "imported_in_source": {
              "markitdown": [
                "shared/adapter_fixtures.py:108"
              ],
              "MarkItDown": [
                "shared/adapter_fixtures.py:108"
              ]
            },
            "stub_only": {
              "markitdown": [
                "app/ingestion/docx_adapter.py:80",
                "app/ingestion/multi_format.py:155"
              ],
              "MarkItDown": [
                "app/ingestion/docx_adapter.py:80",
                "app/ingestion/multi_format.py:155"
              ]
            },
            "mentioned_only": {
              "markitdown": [
                "shared/adapter_contract.py:63",
                "app/ingestion/file.py:64",
                "app/ingestion/pptx_adapter.py:4"
              ],
              "MarkItDown": [
                "shared/adapter_contract.py:63",
                "app/ingestion/file.py:64",
                "app/ingestion/pptx_adapter.py:4"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [
            "legacy.document.convert"
          ],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "document-conversion",
            "legacy.document.convert"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['document-conversion', 'legacy.document.convert'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['document-conversion', 'legacy.document.convert'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "atlas-join-ambiguous",
            "values": {
              "atlas_capability_ids": [
                "CAP-0020",
                "CAP-0100"
              ],
              "note": "more than one atlas capability names this donor or owns its runtime capability; no winner is picked, so the entry cannot claim the plugin class"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "document-conversion",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "legacy.document.convert",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C002",
        "name": "MarkItDown[pdf]",
        "version": "0.1.6 (uv.lock)",
        "canonical_url": "https://github.com/microsoft/markitdown",
        "capability": "document-conversion",
        "code_license": "MIT",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source"
        ],
        "product_path": "app/ingestion/multi_format.py",
        "evidence": "Real legacy conversion: app/ingestion/multi_format.py. shared-contracts/adapters/converters/markitdown_adapter.py is only a txt/md placeholder. Current Core Office/PDF worker is not this adapter.",
        "decision": "Retain existing legacy converter as bounded fallback; do not claim current Core integration or installed qualification for this donor.",
        "upstream_note": "Task wheel metadata MIT; wheel does not contain a LICENSE file. Exact upstream license-file hash remains UNVERIFIED.",
        "history": [
          {
            "recorded_at": "2026-10-08",
            "reason": "Current source/result correction; original claim retained, not deleted.",
            "original_record": {
              "id": "C002",
              "name": "MarkItDown[pdf]",
              "version": "uv.lock",
              "canonical_url": "https://github.com/microsoft/markitdown",
              "capability": "document-conversion",
              "code_license": "MIT",
              "model_license": null,
              "disposition": "CURRENT",
              "qualification": [
                "source",
                "installed"
              ],
              "product_path": "app/ingestion/multi_format.py",
              "evidence": "PDF/DOCX/PPTX/XLSX conversion paths",
              "decision": "Lightweight baseline for text-native PDF and Office. Disable default LLM OCR. pdfminer-six/pdfplumber/pypdfium2 transitive deps recorded separately.",
              "upstream_note": "MIT; optional [docx] group requires separate python-docx decision."
            }
          }
        ],
        "current_task_verification": "docs/current/OSS-REUSE-VERIFICATION-20261008.json"
      },
      "qualification": {
        "stable_key": "markitdown",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "0.1.6 (uv.lock)",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "memos",
      "display_names": [
        "MemOS",
        "Machine experience memory and skill crystallization"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "SIDECAR",
      "classification_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "memos",
        "display_names": [
          "MemOS",
          "Machine experience memory and skill crystallization"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-MEMOS",
            "absorption_mode": "SIDECAR",
            "status": "candidate"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-MEMOS"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "SIDECAR",
        "declared_modes": {
          "capability_absorption_registry": "SIDECAR",
          "capability_absorption_registry_status": "candidate",
          "supply_chain_ledger": null,
          "derived_mode": "SIDECAR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "mentioned_only",
          "carried": false,
          "terms": [
            "MemOS",
            "Machine experience memory and skill crystallization"
          ],
          "hits": {
            "mentioned_only": {
              "MemOS": [
                "app/memory/memory_layers.py:1"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed mentioned_only for terms ['MemOS', 'Machine experience memory and skill crystallization'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
        "conflicts": [
          {
            "reason": "claimed-runtime-adoption-without-donor-artifact",
            "values": {
              "registry_mode": "SIDECAR",
              "registry_status": "candidate",
              "ledger_disposition": null,
              "verification_tier": "D",
              "probed_artifact": "mentioned_only",
              "donor_terms_probed": [
                "MemOS",
                "Machine experience memory and skill crystallization"
              ],
              "ledger_reported_evidence_state": null
            }
          }
        ]
      },
      "ledger": null,
      "qualification": {
        "stable_key": "memos",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SIDECAR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "mineru",
      "display_names": [
        "MinerU"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "mineru",
        "display_names": [
          "MinerU"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "B001",
            "capability": "document-structure"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "B001"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REVIEW-BLOCK",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "MinerU"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "document-structure"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['MinerU'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "document-structure",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "B001",
        "name": "MinerU",
        "canonical_url": "https://github.com/opendatalab/MinerU",
        "capability": "document-structure",
        "code_license": "Apache-2.0 + additional conditions",
        "model_license": "custom",
        "disposition": "REVIEW-BLOCK",
        "decision": "Apache-2.0 + additional MAU/revenue threshold and online-service identification obligations. NOT equal to plain Apache-2.0. Default disabled until owner/legal review.",
        "upstream_note": "Custom conditions in LICENSE.md — do NOT describe as 'Apache-2.0'."
      },
      "qualification": {
        "stable_key": "mineru",
        "disposition": "REVIEW-BLOCK",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0 + additional conditions",
              "weights": "custom"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "mozillareadability",
      "display_names": [
        "Mozilla Readability"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "no single atlas capability joins it: capability ids ['web-extraction-fallback'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "mozillareadability",
        "display_names": [
          "Mozilla Readability"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "A011",
            "capability": "web-extraction-fallback"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A011"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "EVALUATE",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "Mozilla Readability",
            "readabilipy"
          ],
          "hits": {
            "package_declared": {
              "readabilipy": [
                "pyproject.toml:82",
                "uv.lock:3884"
              ]
            },
            "imported_in_source": {
              "readabilipy": [
                "shared/adapter_fixtures.py:153",
                "app/ingestion/multi_format.py:695"
              ]
            },
            "mentioned_only": {
              "Mozilla Readability": [
                "shared/adapter_fixtures.py:552",
                "app/ingestion/multi_format.py:662"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "web-extraction-fallback"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['web-extraction-fallback'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['web-extraction-fallback'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "declared-non-runtime-but-artifact-is-carried",
            "values": {
              "registry_mode": null,
              "ledger_disposition": "EVALUATE",
              "adoption_artifact": "package_declared",
              "hits": {
                "package_declared": {
                  "readabilipy": [
                    "pyproject.toml:82",
                    "uv.lock:3884"
                  ]
                },
                "imported_in_source": {
                  "readabilipy": [
                    "shared/adapter_fixtures.py:153",
                    "app/ingestion/multi_format.py:695"
                  ]
                },
                "mentioned_only": {
                  "Mozilla Readability": [
                    "shared/adapter_fixtures.py:552",
                    "app/ingestion/multi_format.py:662"
                  ]
                }
              }
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "web-extraction-fallback",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A011",
        "name": "Mozilla Readability",
        "canonical_url": "https://github.com/mozilla/readability",
        "capability": "web-extraction-fallback",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "EVALUATE",
        "qualification": [
          "source"
        ],
        "decision": "Second-result fallback when Trafilatura fails or produces high-difference output. Output must still be sanitized (HTML is untrusted).",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "mozillareadability",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "networkx",
      "display_names": [
        "networkx/networkx",
        "NetworkX"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "bound to legacy-path capability ids ['legacy.graph.compute'] rather than a declared route in services/python-workers/routes.json",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "networkx",
        "display_names": [
          "networkx/networkx",
          "NetworkX"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "networkx/networkx",
            "capability_id": "legacy.graph.compute"
          },
          "supply_chain_ledger": {
            "id": "C009",
            "capability": "graph-computation"
          },
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0110",
          "atlas_join_candidates": [
            "CAP-0110"
          ],
          "donor_disposition_archive": [
            "C009"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": "CAP-0110",
        "map_state": "worker_backed",
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "networkx",
            "NetworkX"
          ],
          "hits": {
            "package_declared": {
              "networkx": [
                "pyproject.toml:30",
                "pyproject.toml:57",
                "uv.lock:2503"
              ],
              "NetworkX": [
                "pyproject.toml:30",
                "pyproject.toml:57",
                "uv.lock:2503"
              ]
            },
            "imported_in_source": {
              "networkx": [
                "app/graph/community.py:17",
                "app/memory/graph_db.py:21"
              ],
              "NetworkX": [
                "app/graph/community.py:17",
                "app/memory/graph_db.py:21"
              ]
            },
            "mentioned_only": {
              "networkx": [
                "shared/fact_extractor.py:176",
                "shared/graph_rag.py:4",
                "shared/storage.py:231"
              ],
              "NetworkX": [
                "shared/fact_extractor.py:176",
                "shared/graph_rag.py:4",
                "shared/storage.py:231"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [
            "legacy.graph.compute"
          ],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "graph-computation",
            "legacy.graph.compute"
          ],
          "enableable": false,
          "degrade_reason": "bound to legacy-path capability ids ['legacy.graph.compute'] rather than a declared route in services/python-workers/routes.json",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "bound to legacy-path capability ids ['legacy.graph.compute'] rather than a declared route in services/python-workers/routes.json",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "graph-computation",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "legacy.graph.compute",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C009",
        "name": "NetworkX",
        "version": "uv.lock",
        "canonical_url": "https://github.com/networkx/networkx",
        "capability": "graph-computation",
        "code_license": "BSD-3-Clause",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source"
        ],
        "product_path": "app/memory/graph_db.py; shared/graph_rag.py",
        "evidence": "Graph computation paths",
        "decision": "Derived local graph projection only. Not a second truth layer. Kùzu archived — not a replacement candidate.",
        "upstream_note": "Kùzu upstream archived 2025-10-10; do not select as primary."
      },
      "qualification": {
        "stable_key": "networkx",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "uv.lock",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "BSD-3-Clause",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "openalex",
      "display_names": [
        "OpenAlex"
      ],
      "surface_class": "enableable_plugin",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "atlas capability CAP-0030 exists, config/capability-map.v1.json state is core_native, and imported_in_source evidence names the donor itself.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "openalex",
        "display_names": [
          "OpenAlex"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "OpenAlex",
            "capability_id": "evidence.openalex"
          },
          "supply_chain_ledger": {
            "id": "A020",
            "capability": "evidence-academic-graph"
          },
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0030",
          "atlas_join_candidates": [
            "CAP-0030"
          ],
          "donor_disposition_archive": [
            "A020"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": "CAP-0030",
        "map_state": "core_native",
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "OpenAlex",
            "openalex"
          ],
          "hits": {
            "imported_in_source": {
              "OpenAlex": [
                "shared/evidence_connectors.py:114",
                "shared/public_evidence.py:16"
              ],
              "openalex": [
                "shared/evidence_connectors.py:114",
                "shared/public_evidence.py:16"
              ]
            },
            "mentioned_only": {
              "OpenAlex": [
                "shared/pipeline.py:198"
              ],
              "openalex": [
                "shared/pipeline.py:198"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "evidence-academic-graph",
            "evidence.openalex"
          ],
          "enableable": true,
          "degrade_reason": null,
          "frontend_only_client": false
        },
        "surface_class": "enableable_plugin",
        "surface_class_reason": "atlas capability CAP-0030 exists, config/capability-map.v1.json state is core_native, and imported_in_source evidence names the donor itself.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "evidence-academic-graph",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "evidence.openalex",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A020",
        "name": "OpenAlex",
        "canonical_url": "https://openalex.org/",
        "capability": "evidence-academic-graph",
        "code_license": "freemium API",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Academic entity/citation graph. Freemium — free daily allowance, record service-side cost/caching. API key required.",
        "upstream_note": "API; cost model changes — monitor."
      },
      "qualification": {
        "stable_key": "openalex",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "freemium API",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": true,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "openapispecification",
      "display_names": [
        "OAI/OpenAPI-Specification"
      ],
      "surface_class": "format_spec",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier C is defined as an extracted behaviour/format/test with no runtime adoption implied; the carried reference is a format or protocol contract.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "openapispecification",
        "display_names": [
          "OAI/OpenAPI-Specification"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "OAI/OpenAPI-Specification",
            "capability_id": "contract.openapi"
          },
          "supply_chain_ledger": null,
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": null
        },
        "verification_tier": "C",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": null,
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "OpenAPI-Specification",
            "OpenAPI_Specification"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "contract.openapi"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['OpenAPI-Specification', 'OpenAPI_Specification'])",
          "frontend_only_client": false
        },
        "surface_class": "format_spec",
        "surface_class_reason": "tier C is defined as an extracted behaviour/format/test with no runtime adoption implied; the carried reference is a format or protocol contract.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "contract.openapi",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": null,
      "qualification": {
        "stable_key": "openapispecification",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "C",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "openmaic",
      "display_names": [
        "OpenMAIC",
        "Course DSL, renderer, and interactive learning artifacts"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "CONTRACT_ADAPTER",
      "classification_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "openmaic",
        "display_names": [
          "OpenMAIC",
          "Course DSL, renderer, and interactive learning artifacts"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-OPENMAIC",
            "absorption_mode": "CONTRACT_ADAPTER",
            "status": "candidate"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-OPENMAIC"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "CONTRACT_ADAPTER",
        "declared_modes": {
          "capability_absorption_registry": "CONTRACT_ADAPTER",
          "capability_absorption_registry_status": "candidate",
          "supply_chain_ledger": null,
          "derived_mode": "CONTRACT_ADAPTER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "OpenMAIC",
            "Course DSL, renderer, and interactive learning artifacts"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['OpenMAIC', 'Course DSL, renderer, and interactive learning artifacts'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
        "conflicts": [
          {
            "reason": "claimed-runtime-adoption-without-donor-artifact",
            "values": {
              "registry_mode": "CONTRACT_ADAPTER",
              "registry_status": "candidate",
              "ledger_disposition": null,
              "verification_tier": "D",
              "probed_artifact": "NONE",
              "donor_terms_probed": [
                "OpenMAIC",
                "Course DSL, renderer, and interactive learning artifacts"
              ],
              "ledger_reported_evidence_state": null
            }
          }
        ]
      },
      "ledger": null,
      "qualification": {
        "stable_key": "openmaic",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "CONTRACT_ADAPTER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "opentutor",
      "display_names": [
        "OpenTutor",
        "Adaptive learning blocks and FSRS integration"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "ALGORITHM_DONOR",
      "classification_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "opentutor",
        "display_names": [
          "OpenTutor",
          "Adaptive learning blocks and FSRS integration"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-OPENTUTOR",
            "absorption_mode": "ALGORITHM_DONOR",
            "status": "candidate"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-OPENTUTOR"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "ALGORITHM_DONOR",
        "declared_modes": {
          "capability_absorption_registry": "ALGORITHM_DONOR",
          "capability_absorption_registry_status": "candidate",
          "supply_chain_ledger": null,
          "derived_mode": "ALGORITHM_DONOR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "mentioned_only",
          "carried": false,
          "terms": [
            "OpenTutor",
            "Adaptive learning blocks and FSRS integration"
          ],
          "hits": {
            "mentioned_only": {
              "OpenTutor": [
                "app/learning/learning_path.py:1",
                "app/learning/quiz.py:1",
                "frontend/src/spaces/LearningSpace.tsx:2"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed mentioned_only for terms ['OpenTutor', 'Adaptive learning blocks and FSRS integration'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
        "conflicts": []
      },
      "ledger": null,
      "qualification": {
        "stable_key": "opentutor",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "ALGORITHM_DONOR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "paddleocr",
      "display_names": [
        "PaddleOCR"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "SELF_BUILD_GAP",
      "classification_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "paddleocr",
        "display_names": [
          "PaddleOCR"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "A002",
            "capability": "ocr-chinese-complex"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A002"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "SELF_BUILD_GAP",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "EVALUATE",
          "derived_mode": "SELF_BUILD_GAP"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "stub_only",
          "carried": false,
          "terms": [
            "PaddleOCR"
          ],
          "hits": {
            "stub_only": {
              "PaddleOCR": [
                "shared/bakeoff_engines.py:63"
              ]
            },
            "mentioned_only": {
              "PaddleOCR": [
                "app/ingestion/rapid_ocr_adapter.py:3"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "STUB_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "ocr-chinese-complex"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed stub_only for terms ['PaddleOCR'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "ocr-chinese-complex",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A002",
        "name": "PaddleOCR",
        "canonical_url": "https://github.com/PaddlePaddle/PaddleOCR",
        "capability": "ocr-chinese-complex",
        "code_license": "Apache-2.0",
        "model_license": "per-model record required",
        "disposition": "EVALUATE",
        "qualification": [
          "source"
        ],
        "decision": "Strongest Chinese/mixed candidate. Bake-off against Tesseract/EasyOCR/RapidOCR on fixed Chinese/English scanned corpus. VLM (PP-OCRv5) NOT default.",
        "upstream_note": "Code Apache-2.0; model weights recorded per-model."
      },
      "qualification": {
        "stable_key": "paddleocr",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": "per-model record required"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SELF_BUILD_GAP",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "pdfjs",
      "display_names": [
        "mozilla/pdf.js",
        "PDF.js",
        "pdfjs-dist"
      ],
      "surface_class": "ux_donor",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "the donor is declared only in the client manifest scope (frontend/package.json, frontend/package-lock.json) and no atlas capability joins it, so it is a UI-layer donor.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "pdfjs",
        "display_names": [
          "mozilla/pdf.js",
          "PDF.js",
          "pdfjs-dist"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "mozilla/pdf.js",
            "capability_id": "pdf.read"
          },
          "supply_chain_ledger": {
            "id": "C001",
            "capability": "pdf-viewer"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "C001"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "pdf.js",
            "PDF.js",
            "pdfjs-dist",
            "pdfjs_dist"
          ],
          "hits": {
            "package_declared": {
              "pdfjs-dist": [
                "frontend/package.json:dependencies",
                "frontend/package-lock.json:packages"
              ],
              "pdfjs_dist": [
                "frontend/package.json:dependencies",
                "frontend/package-lock.json:packages"
              ]
            },
            "imported_in_source": {
              "pdf.js": [
                "frontend/src/__tests__/PdfReader.test.tsx:7",
                "frontend/src/components/PdfReader.tsx:3"
              ],
              "PDF.js": [
                "frontend/src/__tests__/PdfReader.test.tsx:7",
                "frontend/src/components/PdfReader.tsx:3"
              ]
            },
            "mentioned_only": {
              "pdf.js": [
                "app/evidence/pdf_serve.py:1",
                "app/workspace/router.py:332",
                "frontend/src/spaces/CanonicalLibrarySpace.tsx:22"
              ],
              "PDF.js": [
                "app/evidence/pdf_serve.py:1",
                "app/workspace/router.py:332",
                "frontend/src/spaces/CanonicalLibrarySpace.tsx:22"
              ],
              "pdfjs-dist": [
                "frontend/src/__tests__/PdfReader.test.tsx:7",
                "frontend/src/components/PdfReader.tsx:3"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "pdf-viewer",
            "pdf.read"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['pdf-viewer', 'pdf.read'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": true
        },
        "surface_class": "ux_donor",
        "surface_class_reason": "the donor is declared only in the client manifest scope (frontend/package.json, frontend/package-lock.json) and no atlas capability joins it, so it is a UI-layer donor.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "pdf-viewer",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "pdf.read",
              "declared_runtime_capabilities_in_the_same_domain": [
                "pdf.extract"
              ],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C001",
        "name": "PDF.js",
        "version": "6.4.299 (frontend/package-lock.json)",
        "canonical_url": "https://github.com/mozilla/pdf.js",
        "capability": "pdf-viewer",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source"
        ],
        "product_path": "frontend/src/components/PdfReader.tsx; frontend/src/spaces/CanonicalLibrarySpace.tsx",
        "evidence": "Current Tauri/React frontend imports locked pdfjs-dist 6.4.299. Native desktop PDF rendering NOT_RUN in OSS task 2026-10-08.",
        "decision": "Existing primary original-PDF reader. Historical removal/Avalonia statement does not describe SUP-022 current authority; source presence is not installed or release qualification.",
        "upstream_note": "Code-license declaration Apache-2.0; installed distribution license hash to be qualified separately.",
        "history": [
          {
            "recorded_at": "2026-10-08",
            "reason": "Current source/result correction; original claim retained, not deleted.",
            "original_record": {
              "id": "C001",
              "name": "PDF.js",
              "version": "6.2.108",
              "canonical_url": "https://github.com/mozilla/pdf.js",
              "capability": "pdf-viewer",
              "code_license": "Apache-2.0",
              "model_license": null,
              "disposition": "REFERENCE",
              "qualification": [],
              "product_path": null,
              "evidence": "Historical loopback UI dependency removed when the duplicate product surface was retired; no PDF.js bytes are packaged or shipped.",
              "decision": "Reference only for the retired React/Tauri shell. Its backend-validated PDF endpoint and sandboxed Blob frame are historical behavior evidence; they do not describe the formal C#/Avalonia desktop PDF path.",
              "upstream_note": "The former 6.2.108 vendored assets and license remain recoverable from Git history but are absent from current release inputs."
            }
          }
        ],
        "current_task_verification": "docs/current/OSS-REUSE-VERIFICATION-20261008.json"
      },
      "qualification": {
        "stable_key": "pdfjs",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "6.4.299 (frontend/package-lock.json)",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "phoenix",
      "display_names": [
        "Phoenix (Arize)"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "phoenix",
        "display_names": [
          "Phoenix (Arize)"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "B008",
            "capability": "observability-ui"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "B008"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REVIEW-BLOCK",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "Phoenix"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "observability-ui"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['Phoenix'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "observability-ui",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "B008",
        "name": "Phoenix (Arize)",
        "canonical_url": "https://github.com/Arize-ai/phoenix",
        "capability": "observability-ui",
        "code_license": "Elastic License 2.0",
        "model_license": null,
        "disposition": "REVIEW-BLOCK",
        "decision": "Elastic License 2.0 — source-available, NOT open-source. Do not list as default OSS dependency. Reference only or independent deployment for evaluation.",
        "upstream_note": "Do not write as 'OSS'. ELv2."
      },
      "qualification": {
        "stable_key": "phoenix",
        "disposition": "REVIEW-BLOCK",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Elastic License 2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "pipaudit",
      "display_names": [
        "pip-audit"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "SIDECAR",
      "classification_reason": "no single atlas capability joins it: capability ids ['dependency-vuln-scan'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "pipaudit",
        "display_names": [
          "pip-audit"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "A023",
            "capability": "dependency-vuln-scan"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A023"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "SIDECAR",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "SIDECAR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "pipeline_invoked",
          "carried": true,
          "terms": [
            "pip-audit",
            "pip_audit"
          ],
          "hits": {
            "pipeline_invoked": {
              "pip-audit": [
                ".github/workflows/ci.yml:159"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "dependency-vuln-scan"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['dependency-vuln-scan'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['dependency-vuln-scan'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "disposition-says-adopted-tier-says-not",
            "values": {
              "verification_tier": "D",
              "supply_chain_disposition": "ADOPT",
              "adoption_artifact": "pipeline_invoked"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "dependency-vuln-scan",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A023",
        "name": "pip-audit",
        "canonical_url": "https://github.com/pypa/pip-audit",
        "capability": "dependency-vuln-scan",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Python dependency vulnerability scan. Part of minimum supply-chain toolset.",
        "upstream_note": null,
        "adopted_revision": "2.10.1",
        "adopted_kind": "CI tool (pinned via uv tool run --from pip-audit==2.10.1)",
        "adopted_wired_at": ".github/workflows/ci.yml test job; report-only until a run is clean"
      },
      "qualification": {
        "stable_key": "pipaudit",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SIDECAR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "prosemirror",
      "display_names": [
        "ProseMirror/prosemirror"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "no donor-specific artifact (probed mentioned_only for terms ['prosemirror'])",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "prosemirror",
        "display_names": [
          "ProseMirror/prosemirror"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "ProseMirror/prosemirror",
            "capability_id": "document.edit"
          },
          "supply_chain_ledger": null,
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": null
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": null,
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "mentioned_only",
          "carried": false,
          "terms": [
            "prosemirror"
          ],
          "hits": {
            "mentioned_only": {
              "prosemirror": [
                "frontend/src/spaces/CanonicalLibrarySpace.tsx:24",
                "frontend/src/test/setup.ts:7"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "document.edit"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed mentioned_only for terms ['prosemirror'])",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no donor-specific artifact (probed mentioned_only for terms ['prosemirror'])",
        "conflicts": [
          {
            "reason": "tier-claims-entry-without-donor-artifact",
            "values": {
              "verification_tier": "B",
              "probed_artifact": "mentioned_only",
              "donor_terms_probed": [
                "prosemirror"
              ],
              "generic_terms_stripped": [],
              "ledger_reported_evidence_state": null
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "document.edit",
              "declared_runtime_capabilities_in_the_same_domain": [
                "document.detect"
              ],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": null,
      "qualification": {
        "stable_key": "prosemirror",
        "disposition": "CURRENT_PAGE_SELECTED",
        "reason": "Current exact lock contains real frontend packages; historical donor classification/route lookup predates integration. Preserve that historical conflict; do not reinterpret document.edit as an installable worker.",
        "activation": {
          "state": "CURRENT_PAGE_REFERENCE_ONLY",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "UF10/O01 current page"
        },
        "evidence": {
          "version": {
            "state": "LOCK_PINNED",
            "value": [
              {
                "name": "prosemirror-changeset",
                "version": "2.4.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-changeset/-/prosemirror-changeset-2.4.4.tgz",
                "integrity": "sha512-Gyuz9jYdrAeA9I7AholyOes9KUmv/lEwsC5O9s5xF5VB3EgTPsXMGUxz4+H1B+wKVPdZbvRcg1Cp3x8qX+8ofA=="
              },
              {
                "name": "prosemirror-commands",
                "version": "1.7.2",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-commands/-/prosemirror-commands-1.7.2.tgz",
                "integrity": "sha512-q6Q6szxqdu9Xd6EcdKsqXghu5nQdZTpB4Q9yd04WRc7/jt763e/rT60Owh0L1GYY+T46o5rD+9lEN36dZS43tw=="
              },
              {
                "name": "prosemirror-dropcursor",
                "version": "1.8.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-dropcursor/-/prosemirror-dropcursor-1.8.4.tgz",
                "integrity": "sha512-VmKxhcA6a+h5oPSYmfF1ZNeQqPbyYaIxqZsKqeYCyTlPtrjUgNaHL3P8vVaO19oqAV0zuaM/axkowZHrB1P3Tg=="
              },
              {
                "name": "prosemirror-gapcursor",
                "version": "1.4.1",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-gapcursor/-/prosemirror-gapcursor-1.4.1.tgz",
                "integrity": "sha512-pMdYaEnjNMSwl11yjEGtgTmLkR08m/Vl+Jj443167p9eB3HVQKhYCc4gmHVDsLPODfZfjr/MmirsdyZziXbQKw=="
              },
              {
                "name": "prosemirror-history",
                "version": "1.5.1",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-history/-/prosemirror-history-1.5.1.tgz",
                "integrity": "sha512-onlwnqKvgtFg6srZOmDOAhlAy1FIHQpOExORybX0S+DvJepE5tPALrB9iGet/2sqqqrelSnB10OoiOJqAvu2DA=="
              },
              {
                "name": "prosemirror-inputrules",
                "version": "1.5.1",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-inputrules/-/prosemirror-inputrules-1.5.1.tgz",
                "integrity": "sha512-7wj4uMjKaXWAQ1CDgxNzNtR9AlsuwzHfdFH1ygEHA2KHF2DOEaXl1CJfNPAKCg9qNEh4rum975QLaCiQPyY6Fw=="
              },
              {
                "name": "prosemirror-keymap",
                "version": "1.2.3",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-keymap/-/prosemirror-keymap-1.2.3.tgz",
                "integrity": "sha512-4HucRlpiLd1IPQQXNqeo81BGtkY8Ai5smHhKW9jjPKRc2wQIxksg7Hl1tTI2IfT2B/LgX6bfYvXxEpJl7aKYKw=="
              },
              {
                "name": "prosemirror-model",
                "version": "1.25.12",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-model/-/prosemirror-model-1.25.12.tgz",
                "integrity": "sha512-Ue2gTmXMa7EhpLNhC7J+h4+ykD8ha12K6rrZFFKKJHBForfIStw5gJ6Zrf1mqqAa9NmpmEB4wp9bKmA4eUVjWg=="
              },
              {
                "name": "prosemirror-schema-list",
                "version": "1.5.1",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-schema-list/-/prosemirror-schema-list-1.5.1.tgz",
                "integrity": "sha512-927lFx/uwyQaGwJxLWCZRkjXG0p48KpMj6ueoYiu4JX05GGuGcgzAy62dfiV8eFZftgyBUvLx76RsMe20fJl+Q=="
              },
              {
                "name": "prosemirror-state",
                "version": "1.4.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-state/-/prosemirror-state-1.4.4.tgz",
                "integrity": "sha512-6jiYHH2CIGbCfnxdHbXZ12gySFY/fz/ulZE333G6bPqIZ4F+TXo9ifiR86nAHpWnfoNjOb3o5ESi7J8Uz1jXHw=="
              },
              {
                "name": "prosemirror-tables",
                "version": "1.8.5",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-tables/-/prosemirror-tables-1.8.5.tgz",
                "integrity": "sha512-V/0cDCsHKHe/tfWkeCmthNUcEp1IVO3p6vwN8XtwE9PZQLAZJigbw3QoraAdfJPir4NKJtNvOB8oYGKRl+t0Dw=="
              },
              {
                "name": "prosemirror-transform",
                "version": "1.12.2",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-transform/-/prosemirror-transform-1.12.2.tgz",
                "integrity": "sha512-PE/aY0HEY4zczvmqrilgkUK/WautF0chvMqkmM/iN5/aPHvwrCWaQZjS6CIZp+K84YrvPFqrL+YArrfJX8xX7g=="
              },
              {
                "name": "prosemirror-view",
                "version": "1.42.6",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/prosemirror-view/-/prosemirror-view-1.42.6.tgz",
                "integrity": "sha512-3g25f6hKV2bBxo3puH3EcYWmmVNSH0iWmNsMVT7sugDSpA025jgpOLarcDWr39SdzPjYMaiYtRdNtXialPSjEQ=="
              }
            ],
            "source_refs": [
              {
                "path": "frontend/package-lock.json",
                "sha256": "bad160497be687b50a3c03241942fce9fff5741f7f2657dc5da953baace48897"
              },
              {
                "path": "frontend/package.json",
                "sha256": "09a223f18536c5ffc6623d4fab21ad453ffc122239056af35d70522d6cc6cf9d"
              }
            ]
          },
          "license": {
            "state": "LOCK_METADATA_AND_OFFICIAL_READBACK",
            "value": {
              "code": "MIT",
              "weights": "NOT_APPLICABLE",
              "official_sources": [
                "https://github.com/ProseMirror/prosemirror-state/blob/master/LICENSE"
              ],
              "official_head_is_not_locked_license_hash": true
            },
            "source_refs": [
              {
                "path": "frontend/package-lock.json",
                "sha256": "bad160497be687b50a3c03241942fce9fff5741f7f2657dc5da953baace48897"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED",
              "execution": "frontend in-process editor; not Python worker",
              "canonical_writer": "Core Document",
              "paid_extensions": "NOT_SELECTED",
              "cloud_collaboration": "NOT_GRANTED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "pymupdf",
      "display_names": [
        "pymupdf/PyMuPDF",
        "PyMuPDF",
        "pymupdf"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "verification tier None is not one of ['A', 'B']",
      "declared_runtime_route": "pdf.extract",
      "original_surface": {
        "stable_key": "pymupdf",
        "display_names": [
          "pymupdf/PyMuPDF",
          "PyMuPDF",
          "pymupdf"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "pymupdf/PyMuPDF",
            "capability_id": "pdf.extract"
          },
          "supply_chain_ledger": null,
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0020",
          "atlas_join_candidates": [
            "CAP-0020"
          ],
          "donor_disposition_archive": null
        },
        "verification_tier": null,
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": null,
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": "CAP-0020",
        "map_state": "worker_backed",
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "PyMuPDF",
            "pymupdf"
          ],
          "hits": {
            "package_declared": {
              "PyMuPDF": [
                "pyproject.toml:28",
                "pyproject.toml:46",
                "pyproject.toml:79"
              ],
              "pymupdf": [
                "pyproject.toml:28",
                "pyproject.toml:46",
                "pyproject.toml:79"
              ]
            },
            "imported_in_source": {
              "PyMuPDF": [
                "crates/archeaxis-api/tests/source_transform_readback.rs:55",
                "crates/archeaxis-application/src/attempts.rs:16",
                "crates/archeaxis-application/tests/pdf_job_end_to_end.rs:157"
              ],
              "pymupdf": [
                "crates/archeaxis-api/tests/source_transform_readback.rs:55",
                "crates/archeaxis-application/src/attempts.rs:16",
                "crates/archeaxis-application/tests/pdf_job_end_to_end.rs:157"
              ]
            },
            "stub_only": {
              "PyMuPDF": [
                "services/python-workers/document/worker_office.py:496",
                "crates/archeaxis-application/src/executor.rs:519",
                "crates/archeaxis-application/tests/pdf_ocr_chain.rs:106"
              ],
              "pymupdf": [
                "services/python-workers/document/worker_office.py:496",
                "crates/archeaxis-application/src/executor.rs:519",
                "crates/archeaxis-application/tests/pdf_ocr_chain.rs:106"
              ]
            },
            "mentioned_only": {
              "PyMuPDF": [
                "shared/media_extractor.py:4",
                "services/python-workers/document/worker_pdf.py:36",
                "services/python-workers/README.md:16"
              ],
              "pymupdf": [
                "shared/media_extractor.py:4",
                "services/python-workers/document/worker_pdf.py:36",
                "services/python-workers/README.md:16"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": "pdf.extract",
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "verification tier None is not one of ['A', 'B']",
          "route_worker_files": [
            "services/python-workers/document/worker_pdf.py"
          ],
          "named_in_route_worker": true,
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "verification tier None is not one of ['A', 'B']",
        "conflicts": []
      },
      "ledger": null,
      "qualification": {
        "stable_key": "pymupdf",
        "disposition": "CURRENT_PAGE_SELECTED",
        "reason": "Existing local PDF route and locked package do not confer redistribution/commercial or packaged desktop qualification. PyMuPDF4LLM is a different REVIEW-BLOCK row.",
        "activation": {
          "state": "CURRENT_PAGE_REFERENCE_ONLY",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "AGPL/commercial combination obligations unresolved for release; no personal/non-profit exemption inferred"
          ],
          "scope": "UF10/O01 current page"
        },
        "evidence": {
          "version": {
            "state": "LOCK_PINNED",
            "value": {
              "package": "pymupdf",
              "version": "1.28.2",
              "source": {
                "registry": "https://pypi.org/simple"
              },
              "pyproject_range_is_not_version": true
            },
            "source_refs": [
              {
                "path": "uv.lock",
                "sha256": "0e3db03c3dcd71e24acc13022839591b575f10e42f1dbdfde8b86ec77fc8f2e3"
              },
              {
                "path": "pyproject.toml",
                "sha256": "8df2995c350abea2dcb4d8b6f13e80c165abe9d7b2f5ca7d503ace3a6006a63c"
              }
            ]
          },
          "license": {
            "state": "LOCAL_DECLARATION_WITH_OFFICIAL_READBACK",
            "value": {
              "code": "AGPL-3.0 or Artifex commercial (installed metadata)",
              "weights": "NOT_APPLICABLE",
              "prior_license_file_sha256": "40e60697600535eabfb5ae05f72829d88cfe8d02dd4792f5a754f6f51dabe55b",
              "official_sources": [
                "https://pymupdf.readthedocs.io/en/latest/about.html#license"
              ],
              "official_head_is_not_locked_license_hash": true
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-REUSE-VERIFICATION-20261008.json",
                "sha256": "67c25efebac6d42ab4a20e82c27b4f771acaffeafff0a5d913cab38b45ae2cf0"
              },
              {
                "path": "uv.lock",
                "sha256": "0e3db03c3dcd71e24acc13022839591b575f10e42f1dbdfde8b86ec77fc8f2e3"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": "pdf.extract",
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED",
              "local_saved_input_only": true,
              "knowledge_writer": "Core only",
              "no_new_network_fetch": true
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": null,
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "pymupdf4llm",
      "display_names": [
        "PyMuPDF4LLM"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "pymupdf4llm",
        "display_names": [
          "PyMuPDF4LLM"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "B002",
            "capability": "pdf-extraction"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "B002"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REVIEW-BLOCK",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "PyMuPDF4LLM"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "pdf-extraction"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['PyMuPDF4LLM'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "pdf-extraction",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "B002",
        "name": "PyMuPDF4LLM",
        "canonical_url": "https://github.com/pymupdf/pymupdf4llm",
        "capability": "pdf-extraction",
        "code_license": "AGPL-3.0",
        "model_license": null,
        "disposition": "REVIEW-BLOCK",
        "decision": "AGPL-3.0. Must explicitly accept AGPL combination obligations or purchase commercial license before any use.",
        "upstream_note": "Do not use under 'personal/non-profit exemption' assumption."
      },
      "qualification": {
        "stable_key": "pymupdf4llm",
        "disposition": "REVIEW-BLOCK",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "AGPL-3.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "pytesseracttesseractocr",
      "display_names": [
        "tesseract-ocr/tesseract",
        "pytesseract + Tesseract-OCR",
        "Tesseract"
      ],
      "surface_class": "enableable_plugin",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "atlas capability CAP-0020 exists, config/capability-map.v1.json state is worker_backed, and package_declared evidence names the donor itself in the declared route image.ocr.",
      "declared_runtime_route": "image.ocr",
      "original_surface": {
        "stable_key": "pytesseracttesseractocr",
        "display_names": [
          "tesseract-ocr/tesseract",
          "pytesseract + Tesseract-OCR",
          "Tesseract"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "tesseract-ocr/tesseract",
            "capability_id": "image.ocr"
          },
          "supply_chain_ledger": {
            "id": "C004",
            "capability": "ocr-image"
          },
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0020",
          "atlas_join_candidates": [
            "CAP-0020"
          ],
          "donor_disposition_archive": [
            "C004"
          ]
        },
        "verification_tier": "A",
        "currently_usable": true,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": "CAP-0020",
        "map_state": "worker_backed",
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "tesseract",
            "pytesseract + Tesseract-OCR",
            "pytesseract + Tesseract_OCR",
            "Tesseract",
            "pytesseract"
          ],
          "hits": {
            "package_declared": {
              "pytesseract": [
                "pyproject.toml:33",
                "pyproject.toml:63",
                "uv.lock:3599"
              ]
            },
            "pipeline_invoked": {
              "tesseract": [
                ".github/workflows/ci.yml:192",
                ".github/workflows/nightly.yml:79",
                "scripts/ci/check_vnext_workers.py:271"
              ],
              "Tesseract": [
                ".github/workflows/ci.yml:192",
                ".github/workflows/nightly.yml:79",
                "scripts/ci/check_vnext_workers.py:271"
              ],
              "pytesseract": [
                ".github/workflows/ci.yml:585"
              ]
            },
            "imported_in_source": {
              "tesseract": [
                "shared/adapter_fixtures.py:81",
                "shared/media_extractor.py:268",
                "services/python-workers/vision/worker_ocr.py:115"
              ],
              "Tesseract": [
                "shared/adapter_fixtures.py:81",
                "shared/media_extractor.py:268",
                "services/python-workers/vision/worker_ocr.py:115"
              ],
              "pytesseract": [
                "shared/adapter_fixtures.py:90",
                "shared/media_extractor.py:255",
                "app/ingestion/ocr_adapter.py:121"
              ]
            },
            "tool_invoked": {
              "tesseract": [
                "tesseract",
                "tesseract-languages",
                "shared/adapter_contract.py:63",
                "shared/adapter_fixtures.py:81"
              ],
              "pytesseract + Tesseract-OCR": [
                "tesseract",
                "tesseract-languages",
                "shared/adapter_contract.py:63",
                "shared/adapter_fixtures.py:81"
              ],
              "pytesseract + Tesseract_OCR": [
                "tesseract",
                "tesseract-languages",
                "shared/adapter_contract.py:63",
                "shared/adapter_fixtures.py:81"
              ],
              "Tesseract": [
                "tesseract",
                "tesseract-languages",
                "shared/adapter_contract.py:63",
                "shared/adapter_fixtures.py:81"
              ]
            },
            "stub_only": {
              "tesseract": [
                "shared/bakeoff_engines.py:24",
                "app/ingestion/multi_format.py:240",
                "app/ingestion/ocr_adapter.py:23"
              ],
              "Tesseract": [
                "shared/bakeoff_engines.py:24",
                "app/ingestion/multi_format.py:240",
                "app/ingestion/ocr_adapter.py:23"
              ],
              "pytesseract": [
                "shared/bakeoff_engines.py:25",
                "app/ingestion/multi_format.py:246"
              ]
            },
            "mentioned_only": {
              "tesseract": [
                "shared/adapter_contract.py:63",
                "services/python-workers/README.md:21",
                "services/python-workers/tool_paths.py:7"
              ],
              "Tesseract": [
                "shared/adapter_contract.py:63",
                "services/python-workers/README.md:21",
                "services/python-workers/tool_paths.py:7"
              ],
              "pytesseract": [
                "app/ingestion/file.py:64"
              ]
            }
          },
          "bound_resource_entries": [
            "tesseract",
            "tesseract-languages"
          ],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": "image.ocr",
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "ocr-image"
          ],
          "enableable": true,
          "degrade_reason": null,
          "route_worker_files": [
            "services/python-workers/vision/worker_ocr.py"
          ],
          "named_in_route_worker": true,
          "frontend_only_client": false
        },
        "surface_class": "enableable_plugin",
        "surface_class_reason": "atlas capability CAP-0020 exists, config/capability-map.v1.json state is worker_backed, and package_declared evidence names the donor itself in the declared route image.ocr.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "ocr-image",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C004",
        "name": "pytesseract + Tesseract-OCR",
        "version": "system binary",
        "canonical_url": "https://github.com/tesseract-ocr/tesseract",
        "capability": "ocr-image",
        "code_license": "Apache-2.0",
        "model_license": "tessdata Apache-2.0",
        "disposition": "CURRENT",
        "qualification": [
          "source",
          "installed"
        ],
        "product_path": "app/ingestion/multi_format.py (_via_image_ocr, MFX-010)",
        "evidence": "Real-image gate; honest unavailable when Tesseract absent",
        "decision": "Baseline OCR. Language packs and Windows binary qualified separately. Not a complete H2 conversion loop yet — EvidenceAnchor per page/block still needed.",
        "upstream_note": "100+ languages via tessdata. Windows packageable."
      },
      "qualification": {
        "stable_key": "pytesseracttesseractocr",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "system binary",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": "tessdata Apache-2.0"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": "image.ocr",
              "enableable_inherited": true,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "A",
              "currently_usable": true,
              "ledger": [
                "source",
                "installed"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "raganything",
      "display_names": [
        "RAG-Anything",
        "Multimodal document parsing and structure extraction"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "raganything",
        "display_names": [
          "RAG-Anything",
          "Multimodal document parsing and structure extraction"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-RAG-ANYTHING",
            "absorption_mode": "PYTHON_WORKER",
            "status": "candidate"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-RAG-ANYTHING"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": "PYTHON_WORKER",
          "capability_absorption_registry_status": "candidate",
          "supply_chain_ledger": null,
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "RAG-Anything",
            "RAG_Anything",
            "Multimodal document parsing and structure extraction"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['RAG-Anything', 'RAG_Anything', 'Multimodal document parsing and structure extraction'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
        "conflicts": [
          {
            "reason": "claimed-runtime-adoption-without-donor-artifact",
            "values": {
              "registry_mode": "PYTHON_WORKER",
              "registry_status": "candidate",
              "ledger_disposition": null,
              "verification_tier": "D",
              "probed_artifact": "NONE",
              "donor_terms_probed": [
                "RAG-Anything",
                "RAG_Anything",
                "Multimodal document parsing and structure extraction"
              ],
              "ledger_reported_evidence_state": null
            }
          }
        ]
      },
      "ledger": null,
      "qualification": {
        "stable_key": "raganything",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "rapidfuzz",
      "display_names": [
        "rapidfuzz/RapidFuzz",
        "RapidFuzz"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "rapidfuzz",
        "display_names": [
          "rapidfuzz/RapidFuzz",
          "RapidFuzz"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "rapidfuzz/RapidFuzz",
            "capability_id": "quality.text.similarity"
          },
          "supply_chain_ledger": {
            "id": "A014",
            "capability": "text-alignment"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A014"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "RapidFuzz",
            "rapidfuzz"
          ],
          "hits": {
            "package_declared": {
              "RapidFuzz": [
                "pyproject.toml:36",
                "pyproject.toml:71",
                "uv.lock:3785"
              ],
              "rapidfuzz": [
                "pyproject.toml:36",
                "pyproject.toml:71",
                "uv.lock:3785"
              ]
            },
            "imported_in_source": {
              "RapidFuzz": [
                "shared/text_quality.py:12"
              ],
              "rapidfuzz": [
                "shared/text_quality.py:12"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "quality.text.similarity",
            "text-alignment"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['quality.text.similarity', 'text-alignment'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "quality.text.similarity",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "text-alignment",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A014",
        "name": "RapidFuzz",
        "canonical_url": "https://github.com/rapidfuzz/RapidFuzz",
        "capability": "text-alignment",
        "code_license": "MIT",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Candidate text alignment and difference localization. Does NOT arbitrate factual correctness. Used to locate DisagreementSpan positions.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "rapidfuzz",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "rapidocr",
      "display_names": [
        "RapidAI/RapidOCR",
        "RapidOCR"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "SIDECAR",
      "classification_reason": "no single atlas capability joins it: capability ids ['legacy.image.ocr', 'ocr-windows-cpu'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "rapidocr",
        "display_names": [
          "RapidAI/RapidOCR",
          "RapidOCR"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "RapidAI/RapidOCR",
            "capability_id": "legacy.image.ocr"
          },
          "supply_chain_ledger": {
            "id": "A004",
            "capability": "ocr-windows-cpu"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A004"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "SIDECAR",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "EVALUATE",
          "derived_mode": "SIDECAR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "tool_invoked",
          "carried": true,
          "terms": [
            "RapidOCR"
          ],
          "hits": {
            "tool_invoked": {
              "RapidOCR": [
                "rapidocr",
                "rapidocr-ppocr-onnx",
                "shared/bakeoff_engines.py:8",
                "app/ingestion/rapid_ocr_adapter.py:1"
              ]
            },
            "stub_only": {
              "RapidOCR": [
                "shared/bakeoff_engines.py:115",
                "app/ingestion/rapid_ocr_adapter.py:17"
              ]
            },
            "mentioned_only": {
              "RapidOCR": [
                "services/python-workers/README.md:32"
              ]
            }
          },
          "bound_resource_entries": [
            "rapidocr"
          ],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [
            "legacy.image.ocr"
          ],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "legacy.image.ocr",
            "ocr-windows-cpu"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['legacy.image.ocr', 'ocr-windows-cpu'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['legacy.image.ocr', 'ocr-windows-cpu'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "tier-says-implemented-disposition-says-not",
            "values": {
              "verification_tier": "B",
              "supply_chain_disposition": "EVALUATE",
              "adoption_artifact": "tool_invoked",
              "source": "docs/current/OSS-REUSE-DECISIONS-20261008.json vs docs/truth/SUPPLY_CHAIN_LEDGER.json"
            }
          },
          {
            "reason": "declared-non-runtime-but-artifact-is-carried",
            "values": {
              "registry_mode": null,
              "ledger_disposition": "EVALUATE",
              "adoption_artifact": "tool_invoked",
              "hits": {
                "tool_invoked": {
                  "RapidOCR": [
                    "rapidocr",
                    "rapidocr-ppocr-onnx",
                    "shared/bakeoff_engines.py:8",
                    "app/ingestion/rapid_ocr_adapter.py:1"
                  ]
                },
                "stub_only": {
                  "RapidOCR": [
                    "shared/bakeoff_engines.py:115",
                    "app/ingestion/rapid_ocr_adapter.py:17"
                  ]
                },
                "mentioned_only": {
                  "RapidOCR": [
                    "services/python-workers/README.md:32"
                  ]
                }
              }
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "legacy.image.ocr",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "ocr-windows-cpu",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A004",
        "name": "RapidOCR",
        "canonical_url": "https://github.com/RapidAI/RapidOCR",
        "capability": "ocr-windows-cpu",
        "code_license": "Apache-2.0",
        "model_license": "derived-model source review required",
        "disposition": "EVALUATE",
        "qualification": [
          "source"
        ],
        "decision": "Windows/CPU/ONNX potential. Model hash and derivation chain must pass review before selection.",
        "upstream_note": "Derived models — verify right chain."
      },
      "qualification": {
        "stable_key": "rapidocr",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": "derived-model source review required"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SIDECAR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "searxng",
      "display_names": [
        "SearXNG"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "searxng",
        "display_names": [
          "SearXNG"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "B009",
            "capability": "search-aggregation"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "B009"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REVIEW-BLOCK",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "SearXNG"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "search-aggregation"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['SearXNG'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "search-aggregation",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "B009",
        "name": "SearXNG",
        "canonical_url": "https://github.com/searxng/searxng",
        "capability": "search-aggregation",
        "code_license": "AGPL-3.0",
        "model_license": null,
        "disposition": "REVIEW-BLOCK",
        "decision": "AGPL-3.0. Optional sidecar for self-hosted search discovery. Cannot embed and claim permissive license.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "searxng",
        "disposition": "REVIEW-BLOCK",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "AGPL-3.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "sherpaonnx",
      "display_names": [
        "k2-fsa/sherpa-onnx",
        "sherpa-onnx"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "no single atlas capability joins it: capability ids ['asr-streaming', 'media.transcribe.sensevoice'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "sherpaonnx",
        "display_names": [
          "k2-fsa/sherpa-onnx",
          "sherpa-onnx"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "k2-fsa/sherpa-onnx",
            "capability_id": "media.transcribe.sensevoice"
          },
          "supply_chain_ledger": {
            "id": "A007",
            "capability": "asr-streaming"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A007"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "EVALUATE",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "sherpa-onnx",
            "sherpa_onnx"
          ],
          "hits": {
            "package_declared": {
              "sherpa-onnx": [
                "pyproject.toml:115",
                "uv.lock:4426"
              ],
              "sherpa_onnx": [
                "pyproject.toml:115",
                "uv.lock:4426"
              ]
            },
            "tool_invoked": {
              "sherpa-onnx": [
                "rapidocr-ppocr-onnx",
                "sherpa-onnx",
                "services/python-workers/media/worker_diarize.py:4",
                "app/ingestion/asr_adapter.py:107"
              ],
              "sherpa_onnx": [
                "rapidocr-ppocr-onnx",
                "sherpa-onnx",
                "services/python-workers/media/worker_diarize.py:4",
                "app/ingestion/asr_adapter.py:107"
              ]
            },
            "mentioned_only": {
              "sherpa-onnx": [
                "services/python-workers/media/worker_diarize.py:4",
                "app/ingestion/asr_adapter.py:107"
              ],
              "sherpa_onnx": [
                "services/python-workers/media/worker_diarize.py:114",
                "app/ingestion/asr_adapter.py:148"
              ]
            }
          },
          "bound_resource_entries": [
            "sherpa-onnx",
            "sherpa-onnx-speaker-diarization"
          ],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "asr-streaming",
            "media.transcribe.sensevoice"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['asr-streaming', 'media.transcribe.sensevoice'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['asr-streaming', 'media.transcribe.sensevoice'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "tier-says-implemented-disposition-says-not",
            "values": {
              "verification_tier": "B",
              "supply_chain_disposition": "EVALUATE",
              "adoption_artifact": "package_declared",
              "source": "docs/current/OSS-REUSE-DECISIONS-20261008.json vs docs/truth/SUPPLY_CHAIN_LEDGER.json"
            }
          },
          {
            "reason": "declared-non-runtime-but-artifact-is-carried",
            "values": {
              "registry_mode": null,
              "ledger_disposition": "EVALUATE",
              "adoption_artifact": "package_declared",
              "hits": {
                "package_declared": {
                  "sherpa-onnx": [
                    "pyproject.toml:115",
                    "uv.lock:4426"
                  ],
                  "sherpa_onnx": [
                    "pyproject.toml:115",
                    "uv.lock:4426"
                  ]
                },
                "tool_invoked": {
                  "sherpa-onnx": [
                    "rapidocr-ppocr-onnx",
                    "sherpa-onnx",
                    "services/python-workers/media/worker_diarize.py:4",
                    "app/ingestion/asr_adapter.py:107"
                  ],
                  "sherpa_onnx": [
                    "rapidocr-ppocr-onnx",
                    "sherpa-onnx",
                    "services/python-workers/media/worker_diarize.py:4",
                    "app/ingestion/asr_adapter.py:107"
                  ]
                },
                "mentioned_only": {
                  "sherpa-onnx": [
                    "services/python-workers/media/worker_diarize.py:4",
                    "app/ingestion/asr_adapter.py:107"
                  ],
                  "sherpa_onnx": [
                    "services/python-workers/media/worker_diarize.py:114",
                    "app/ingestion/asr_adapter.py:148"
                  ]
                }
              }
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "asr-streaming",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "media.transcribe.sensevoice",
              "declared_runtime_capabilities_in_the_same_domain": [
                "media.diarize",
                "media.probe",
                "media.transcribe",
                "media.video"
              ],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A007",
        "name": "sherpa-onnx",
        "canonical_url": "https://github.com/k2-fsa/sherpa-onnx",
        "capability": "asr-streaming",
        "code_license": "Apache-2.0",
        "model_license": "per-model record required",
        "disposition": "EVALUATE",
        "qualification": [
          "source"
        ],
        "decision": "Multi-platform/offline streaming ASR. Evaluate for specific language/streaming scenarios. Each model registered individually.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "sherpaonnx",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": "per-model record required"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "silerovad",
      "display_names": [
        "snakers4/silero-vad",
        "Silero VAD"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "SELF_BUILD_GAP",
      "classification_reason": "tier B claims an implementation or entry, but no donor-specific artifact was found in any dependency manifest, vendor root, source identifier, pipeline invocation or bound resource index.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "silerovad",
        "display_names": [
          "snakers4/silero-vad",
          "Silero VAD"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "snakers4/silero-vad",
            "capability_id": "legacy.audio.vad"
          },
          "supply_chain_ledger": {
            "id": "A008",
            "capability": "voice-activity-detection"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A008"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "SELF_BUILD_GAP",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "SELF_BUILD_GAP"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "stub_only",
          "carried": false,
          "terms": [
            "silero-vad",
            "silero_vad",
            "Silero VAD",
            "silero"
          ],
          "hits": {
            "stub_only": {
              "silero": [
                "shared/audio_vad.py:15"
              ]
            },
            "mentioned_only": {
              "silero-vad": [
                "shared/audio_vad.py:19"
              ],
              "silero_vad": [
                "shared/audio_vad.py:12"
              ],
              "Silero VAD": [
                "shared/audio_vad.py:1"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [
            "legacy.audio.vad"
          ],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "legacy.audio.vad",
            "voice-activity-detection"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed stub_only for terms ['silero-vad', 'silero_vad', 'Silero VAD', 'silero'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier B claims an implementation or entry, but no donor-specific artifact was found in any dependency manifest, vendor root, source identifier, pipeline invocation or bound resource index.",
        "conflicts": [
          {
            "reason": "tier-claims-entry-without-donor-artifact",
            "values": {
              "verification_tier": "B",
              "probed_artifact": "stub_only",
              "donor_terms_probed": [
                "silero-vad",
                "silero_vad",
                "Silero VAD",
                "silero"
              ],
              "generic_terms_stripped": [
                "activity",
                "detection",
                "vad",
                "voice"
              ],
              "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
            }
          },
          {
            "reason": "claimed-runtime-adoption-without-donor-artifact",
            "values": {
              "registry_mode": null,
              "registry_status": null,
              "ledger_disposition": "ADOPT",
              "verification_tier": "B",
              "probed_artifact": "stub_only",
              "donor_terms_probed": [
                "silero-vad",
                "silero_vad",
                "Silero VAD",
                "silero"
              ],
              "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
            }
          },
          {
            "reason": "donor-disposition-check-credits-a-generic-term",
            "values": {
              "evidence_state_from_donor_check": "IMPLEMENTED_IN_SOURCE",
              "donor_specific_artifact": "stub_only",
              "donor_terms_probed": [
                "silero-vad",
                "silero_vad",
                "Silero VAD",
                "silero"
              ],
              "generic_terms_stripped": [
                "activity",
                "detection",
                "vad",
                "voice"
              ],
              "note": "the disposition check probes the row's curated terms, which include the capability's own name; crediting this donor on those hits is the failure mode this crosswalk exists to refuse"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "legacy.audio.vad",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "voice-activity-detection",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A008",
        "name": "Silero VAD",
        "canonical_url": "https://github.com/snakers4/silero-vad",
        "capability": "voice-activity-detection",
        "code_license": "MIT",
        "model_license": "MIT",
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Local small model. Reduces silent-segment inference and hallucination. Retain timeline for EvidenceAnchor.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "silerovad",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": "MIT"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SELF_BUILD_GAP",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "sqlitevec",
      "display_names": [
        "asg017/sqlite-vec",
        "sqlite-vec"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
      "declared_runtime_route": "search.semantic",
      "original_surface": {
        "stable_key": "sqlitevec",
        "display_names": [
          "asg017/sqlite-vec",
          "sqlite-vec"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "asg017/sqlite-vec",
            "capability_id": "search.semantic"
          },
          "supply_chain_ledger": {
            "id": "C008",
            "capability": "vector-index"
          },
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0110",
          "atlas_join_candidates": [
            "CAP-0110"
          ],
          "donor_disposition_archive": [
            "C008"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": "CAP-0110",
        "map_state": "worker_backed",
        "adoption": {
          "artifact": "mentioned_only",
          "carried": false,
          "terms": [
            "vec0"
          ],
          "hits": {
            "mentioned_only": {
              "vec0": [
                "shared/index_manifest.py:197",
                "shared/migration_runner.py:288",
                "app/memory/vector_db.py:4"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": "search.semantic",
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "vector-index"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed mentioned_only for terms ['vec0'])",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
        "conflicts": [
          {
            "reason": "tier-claims-entry-without-donor-artifact",
            "values": {
              "verification_tier": "B",
              "probed_artifact": "mentioned_only",
              "donor_terms_probed": [
                "vec0"
              ],
              "generic_terms_stripped": [
                "index",
                "vector",
                "vi"
              ],
              "ledger_reported_evidence_state": "DECLARED"
            }
          },
          {
            "reason": "claimed-runtime-adoption-without-donor-artifact",
            "values": {
              "registry_mode": null,
              "registry_status": null,
              "ledger_disposition": "CURRENT",
              "verification_tier": "B",
              "probed_artifact": "mentioned_only",
              "donor_terms_probed": [
                "vec0"
              ],
              "ledger_reported_evidence_state": "DECLARED"
            }
          },
          {
            "reason": "donor-disposition-check-credits-a-generic-term",
            "values": {
              "evidence_state_from_donor_check": "DECLARED",
              "donor_specific_artifact": "mentioned_only",
              "donor_terms_probed": [
                "vec0"
              ],
              "generic_terms_stripped": [
                "index",
                "vector",
                "vi"
              ],
              "note": "the disposition check probes the row's curated terms, which include the capability's own name; crediting this donor on those hits is the failure mode this crosswalk exists to refuse"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "vector-index",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C008",
        "name": "sqlite-vec",
        "version": "uv.lock",
        "canonical_url": "https://github.com/asg017/sqlite-vec",
        "capability": "vector-index",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source"
        ],
        "product_path": "app/memory/vector_db.py",
        "evidence": "Vector search tests",
        "decision": "Optional derived index. FTS5 always available as independent fallback. Vector index can be deleted and rebuilt. Only switch to LanceDB if scale/corpus proves FTS5+sqlite-vec insufficient.",
        "upstream_note": "Dual-license files; verify exact grant."
      },
      "qualification": {
        "stable_key": "sqlitevec",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "uv.lock",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": "search.semantic",
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "structlog",
      "display_names": [
        "hynek/structlog",
        "structlog"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "structlog",
        "display_names": [
          "hynek/structlog",
          "structlog"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "hynek/structlog",
            "capability_id": "runtime.structured-logging"
          },
          "supply_chain_ledger": {
            "id": "C011",
            "capability": "structured-logging"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "C011"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "structlog"
          ],
          "hits": {
            "package_declared": {
              "structlog": [
                "pyproject.toml:26",
                "pyproject.toml:69",
                "uv.lock:4557"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "runtime.structured-logging",
            "structured-logging"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['runtime.structured-logging', 'structured-logging'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "carried as substrate (declared package, vendored copy, imported code, invoked pipeline tool or bound external resource) with no atlas capability join and no declared worker route to enable.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "runtime.structured-logging",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "structured-logging",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C011",
        "name": "structlog",
        "version": "uv.lock",
        "canonical_url": "https://github.com/hynek/structlog",
        "capability": "structured-logging",
        "code_license": "MIT OR Apache-2.0",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source",
          "installed"
        ],
        "product_path": "Direct dependency",
        "evidence": "Structured log foundation",
        "decision": "Converge responsibilities with Loguru — avoid maintaining two active log frameworks. One should be deprecated or scoped.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "structlog",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "uv.lock",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT OR Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source",
                "installed"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "syft",
      "display_names": [
        "anchore/syft",
        "Syft"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier D is an authored review verdict: a deferred candidate with a stated demand trigger and no adoption. Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "syft",
        "display_names": [
          "anchore/syft",
          "Syft"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "anchore/syft",
            "capability_id": "sbom.tool"
          },
          "supply_chain_ledger": {
            "id": "A022",
            "capability": "sbom-generator"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A022"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "syft",
            "Syft"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "sbom-generator",
            "sbom.tool"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['syft', 'Syft'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D is an authored review verdict: a deferred candidate with a stated demand trigger and no adoption. Neither is an adoption.",
        "conflicts": [
          {
            "reason": "disposition-says-adopted-tier-says-not",
            "values": {
              "verification_tier": "D",
              "supply_chain_disposition": "ADOPT",
              "adoption_artifact": "NONE"
            }
          },
          {
            "reason": "claimed-runtime-adoption-without-donor-artifact",
            "values": {
              "registry_mode": null,
              "registry_status": null,
              "ledger_disposition": "ADOPT",
              "verification_tier": "D",
              "probed_artifact": "NONE",
              "donor_terms_probed": [
                "syft",
                "Syft"
              ],
              "ledger_reported_evidence_state": "NONE"
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "sbom-generator",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "sbom.tool",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A022",
        "name": "Syft",
        "canonical_url": "https://github.com/anchore/syft",
        "capability": "sbom-generator",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "SBOM generation. Bound to build artifact. H5 release qualification.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "syft",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "Apache-2.0",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "tiptap",
      "display_names": [
        "ueberdosis/tiptap",
        "Tiptap"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "no single atlas capability joins it: capability ids ['document.edit'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "tiptap",
        "display_names": [
          "ueberdosis/tiptap",
          "Tiptap"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "ueberdosis/tiptap",
            "capability_id": "document.edit"
          },
          "supply_chain_ledger": null,
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": null
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": null,
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "tiptap",
            "Tiptap"
          ],
          "hits": {
            "imported_in_source": {
              "tiptap": [
                "frontend/src/__tests__/CanonicalLibrarySpace.test.tsx:1",
                "frontend/src/__tests__/CanonicalReviewLearning.test.tsx:1",
                "frontend/src/__tests__/TemplateBindings.test.tsx:55"
              ],
              "Tiptap": [
                "frontend/src/__tests__/CanonicalLibrarySpace.test.tsx:1",
                "frontend/src/__tests__/CanonicalReviewLearning.test.tsx:1",
                "frontend/src/__tests__/TemplateBindings.test.tsx:55"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "document.edit"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['document.edit'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['document.edit'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "document.edit",
              "declared_runtime_capabilities_in_the_same_domain": [
                "document.detect"
              ],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": null,
      "qualification": {
        "stable_key": "tiptap",
        "disposition": "CURRENT_PAGE_SELECTED",
        "reason": "Current exact lock contains real frontend packages; historical donor classification/route lookup predates integration. Preserve that historical conflict; do not reinterpret document.edit as an installable worker.",
        "activation": {
          "state": "CURRENT_PAGE_REFERENCE_ONLY",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "UF10/O01 current page"
        },
        "evidence": {
          "version": {
            "state": "LOCK_PINNED",
            "value": [
              {
                "name": "@tiptap/core",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/core/-/core-3.31.4.tgz",
                "integrity": "sha512-cIVUQYBycighzsk6GbmCef8ZiEDVxoT5EuAe4xg2q9dNkDqCXVqI4YGr9aavCQEiAS4uHiRwqvcsPqJHipFDfg=="
              },
              {
                "name": "@tiptap/extension-blockquote",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-blockquote/-/extension-blockquote-3.31.4.tgz",
                "integrity": "sha512-FHnbvCIW0eDKgUUFjmvEB0ax9YUBW7/Unm+38qpuQROvU872yRqhnDtycKT9IKk46jNdjM4A4fAGUbge10CrAA=="
              },
              {
                "name": "@tiptap/extension-bold",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-bold/-/extension-bold-3.31.4.tgz",
                "integrity": "sha512-QX1xoXvO0gz6uVsoLegumqQ4MJXL7lcUDQZ4J7la7LBqiIh4efrCmp2EXbhpr37M/YQL7w8q3g7H/VovSh7xIg=="
              },
              {
                "name": "@tiptap/extension-bubble-menu",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-bubble-menu/-/extension-bubble-menu-3.31.4.tgz",
                "integrity": "sha512-Ml/yswuys+3QkOMajfXyAGlUKCxEbT3dMyF8vHwQ5mDk9MDm+dqp10It5CrDBkUT/KkVTa6AJI3kb0TXZJZiAA=="
              },
              {
                "name": "@tiptap/extension-bullet-list",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-bullet-list/-/extension-bullet-list-3.31.4.tgz",
                "integrity": "sha512-gHn1RDR4olCnmKpH+G9x+f8R+iKPNVdLlvbFkIpR/stjabZi7fB4Rr5GiHWsulbtxAjdQrNjnVeNdGM4rBxApw=="
              },
              {
                "name": "@tiptap/extension-code",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-code/-/extension-code-3.31.4.tgz",
                "integrity": "sha512-pzi8GNDs5J1DEoO1HNYiJ5WZpgOZzlc/2VIa77mMpEuD4hZxuK0BQzlF/O6Ps/O5P1lGJT4xS0Yowpzb9mD9RA=="
              },
              {
                "name": "@tiptap/extension-code-block",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-code-block/-/extension-code-block-3.31.4.tgz",
                "integrity": "sha512-su/B/cfQ1HpiHl6JfJ6wa+RVEptiYsV4dCntE8XQNj2dUcII4y6w6PQbbswOoDrU79uXHsAvpy44215rghG4LA=="
              },
              {
                "name": "@tiptap/extension-document",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-document/-/extension-document-3.31.4.tgz",
                "integrity": "sha512-vT20u62RWR+BLIyNJ54e24MPUY4zm8VF7tcgJnxQXi7BgVJWcNMtMWWDIkPJ4JNXwfoIznKh3jzYsaYmbCJgQQ=="
              },
              {
                "name": "@tiptap/extension-dropcursor",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-dropcursor/-/extension-dropcursor-3.31.4.tgz",
                "integrity": "sha512-5TbCPCC4RL+QT1NYHjXCYDBHBtVqYOFvFEnk3v98lvXCM2PNL13ofXUfJPuykAVy1OdTAx4DlZOQAD9WKy/IdQ=="
              },
              {
                "name": "@tiptap/extension-floating-menu",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-floating-menu/-/extension-floating-menu-3.31.4.tgz",
                "integrity": "sha512-pKzulkDmolpVt7IP9FSPsC5pKbXQ5pyeqkaAYr8cyOVW+KUObpPRIzAuXvEso8PCjWgwJ1f2qyishOEMw8MbfQ=="
              },
              {
                "name": "@tiptap/extension-gapcursor",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-gapcursor/-/extension-gapcursor-3.31.4.tgz",
                "integrity": "sha512-hBogUAepQH6IQUhaePhPWzQ1Oeu+yqlJVMKO06Eue5m36uRy1PZZAQ780pCGT0SC4R5MH2td1N8EUQ7bupQdDA=="
              },
              {
                "name": "@tiptap/extension-hard-break",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-hard-break/-/extension-hard-break-3.31.4.tgz",
                "integrity": "sha512-oLNajLyUvRMg1qtzFgKGduygTlpaHFB9PU+M+pUWdA4sa1bRnxS2Y++Ao4lHYopJ7nxatLndrYoCIHkotqkPDQ=="
              },
              {
                "name": "@tiptap/extension-heading",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-heading/-/extension-heading-3.31.4.tgz",
                "integrity": "sha512-KqlSeLathpdxCc3kVHBCA/RkHvb+V7u5vgiSEu1Cv3L70r7F19COMGODav/k1AGYBgEXKL6lM9cy8cloE5/28g=="
              },
              {
                "name": "@tiptap/extension-horizontal-rule",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-horizontal-rule/-/extension-horizontal-rule-3.31.4.tgz",
                "integrity": "sha512-ws0Kh8kfHL7ESILSXj0HJAXs8G10ewlW1sedXKm8dm0op9L8il+xl8bEJVoqG/jMf77900Fc2CaQldcCGRpF1g=="
              },
              {
                "name": "@tiptap/extension-italic",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-italic/-/extension-italic-3.31.4.tgz",
                "integrity": "sha512-pftTQBPYZocNDAj/u6OyDIp7YxmN0+N895cQPogJQ6qMHdLiRhzgawiEewJkniyN1w8k3Wx/Etp8pTKrxaOOBQ=="
              },
              {
                "name": "@tiptap/extension-link",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-link/-/extension-link-3.31.4.tgz",
                "integrity": "sha512-LLxW3qfeL9gvDdMPVdxYFYZ0zZSjsoIDhOqjJ5U2UfaK3U2iwkKTBgV2qT+FWf3uUHmBRjBZ08q3dRPmWBAD5g=="
              },
              {
                "name": "@tiptap/extension-list",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-list/-/extension-list-3.31.4.tgz",
                "integrity": "sha512-Wd4YRYxOdf+TtF33/QsRo1RK1CecVxjYGjUBIKNGHAywfh8tghgV4YOUCiV1iJqYt2IBs+RWlIqTmdIPzBrd4A=="
              },
              {
                "name": "@tiptap/extension-list-item",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-list-item/-/extension-list-item-3.31.4.tgz",
                "integrity": "sha512-ao8XAPvhOrtGFILs+fKtOM91omDSpUC8X19m44gbaq5xJDVpIMZ0rP+NAVUS72G7LskhcHa0bu/Pm022bUVjVw=="
              },
              {
                "name": "@tiptap/extension-list-keymap",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-list-keymap/-/extension-list-keymap-3.31.4.tgz",
                "integrity": "sha512-etdkl/YnYfwtALDxecJ+4WYgJAez1fn1vzzZqJklZBpgqiZtny3NxpvWS7/JhsltNG84Wo/oovpfJgVmzhddrw=="
              },
              {
                "name": "@tiptap/extension-ordered-list",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-ordered-list/-/extension-ordered-list-3.31.4.tgz",
                "integrity": "sha512-UNWyF+Dhm08znszIMnT8Y2kJ1lvtiCvUGs1aG7m9cPHxDa7VycWnOqdtXWkc+6xRLNiC0zgWCFWgLLHduV8pRQ=="
              },
              {
                "name": "@tiptap/extension-paragraph",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-paragraph/-/extension-paragraph-3.31.4.tgz",
                "integrity": "sha512-WZlBgw+XVKXerRlmEsoQ7x1PwSU+dh3X+b70+ViZsLebdfsmmYBIaNDrvIGwG9UQr5eLnddJnZplMSTI2YKs+g=="
              },
              {
                "name": "@tiptap/extension-strike",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-strike/-/extension-strike-3.31.4.tgz",
                "integrity": "sha512-4MBr63TJIMqxCjE+gAPdlY1IdELgvbAP516K3Ntn/BkcpEbEoPMEYVz+XTxULyHQEuARDO6jsXPPxRXpA74jaw=="
              },
              {
                "name": "@tiptap/extension-text",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-text/-/extension-text-3.31.4.tgz",
                "integrity": "sha512-WL2ZRpFksgQcXJN05/UQH09YCH9LlhdLrSEcviASvEH/aAfsKiJlDrouN8PET+YAWK/F5xFc5/Q1z0xj+I23jw=="
              },
              {
                "name": "@tiptap/extension-underline",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extension-underline/-/extension-underline-3.31.4.tgz",
                "integrity": "sha512-0iFGPIqmqGkCrOFh1OPo7Dzv5s86dVN3bZaugsz0jK04otkb8bn04ZDKP2/6Wq+lcK0M9DfJ0QqfW5hC2nBZxQ=="
              },
              {
                "name": "@tiptap/extensions",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/extensions/-/extensions-3.31.4.tgz",
                "integrity": "sha512-nIupIne/sHpV2Kw1M4MOmr4+G454KI8BXM5+LWKOU2EpzfALZWVSy7koF9lVRna4Zp5Gv8hfg5Z8kvmrYQvhkw=="
              },
              {
                "name": "@tiptap/pm",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/pm/-/pm-3.31.4.tgz",
                "integrity": "sha512-x7dwth79cQp4QGae66/RJqMDJQv0+n7b7dD7cyFQBWqzPFLJxN/4paHY4qbWedZjNLhRyIOAD9a5q4AYM1zmPA=="
              },
              {
                "name": "@tiptap/react",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/react/-/react-3.31.4.tgz",
                "integrity": "sha512-mBvvXgdPhMinT1NPfwHvFK1dFdMXHVWMSeNn0IPj7/zV0XBmOnASkEOwoIvl8NluKYEtpZBE1yA+6pN2enLa5g=="
              },
              {
                "name": "@tiptap/starter-kit",
                "version": "3.31.4",
                "license": "MIT",
                "resolved": "https://registry.npmjs.org/@tiptap/starter-kit/-/starter-kit-3.31.4.tgz",
                "integrity": "sha512-u7HIJ9vK6kFe4S4J2CIcDLrhRZzoTMSyU0XxjQ6lUNF7pWW3rMi//pvi8RcsZmxGjyb8CpXAqYgNl7f9WyaUeA=="
              }
            ],
            "source_refs": [
              {
                "path": "frontend/package-lock.json",
                "sha256": "bad160497be687b50a3c03241942fce9fff5741f7f2657dc5da953baace48897"
              },
              {
                "path": "frontend/package.json",
                "sha256": "09a223f18536c5ffc6623d4fab21ad453ffc122239056af35d70522d6cc6cf9d"
              }
            ]
          },
          "license": {
            "state": "LOCK_METADATA_AND_OFFICIAL_READBACK",
            "value": {
              "code": "MIT",
              "weights": "NOT_APPLICABLE",
              "official_sources": [
                "https://github.com/ueberdosis/tiptap/blob/main/LICENSE.md"
              ],
              "official_head_is_not_locked_license_hash": true
            },
            "source_refs": [
              {
                "path": "frontend/package-lock.json",
                "sha256": "bad160497be687b50a3c03241942fce9fff5741f7f2657dc5da953baace48897"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED",
              "execution": "frontend in-process editor; not Python worker",
              "canonical_writer": "Core Document",
              "paid_extensions": "NOT_SELECTED",
              "cloud_collaboration": "NOT_GRANTED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "tldraw",
      "display_names": [
        "tldraw"
      ],
      "surface_class": "not_adopted",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "tldraw",
        "display_names": [
          "tldraw"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "B005",
            "capability": "canvas-drawing"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "B005"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "REVIEW-BLOCK",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "tldraw"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "canvas-drawing"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['tldraw'])",
          "frontend_only_client": false
        },
        "surface_class": "not_adopted",
        "surface_class_reason": "tier E or disposition REVIEW-BLOCK: not adopted for the stated role, with the recorded alternative kept in the source row.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "canvas-drawing",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "B005",
        "name": "tldraw",
        "canonical_url": "https://github.com/tldraw/tldraw",
        "capability": "canvas-drawing",
        "code_license": "custom (production requires license key)",
        "model_license": null,
        "disposition": "REVIEW-BLOCK",
        "decision": "License requires a key for production use. NOT an open-source default component. Defer to H7+ as a commercial option.",
        "upstream_note": "Dev environment OK; production requires license key. Do not treat as OSS."
      },
      "qualification": {
        "stable_key": "tldraw",
        "disposition": "REVIEW-BLOCK",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification",
            "Explicit license/combination approval or rejection reversal required before use"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "custom (production requires license key)",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "trafilatura",
      "display_names": [
        "adbar/trafilatura",
        "Trafilatura",
        "trafilatura"
      ],
      "surface_class": "enableable_plugin",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "atlas capability CAP-0020 exists, config/capability-map.v1.json state is worker_backed, and package_declared evidence names the donor itself in the declared route html.structure.",
      "declared_runtime_route": "html.structure",
      "original_surface": {
        "stable_key": "trafilatura",
        "display_names": [
          "adbar/trafilatura",
          "Trafilatura",
          "trafilatura"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "adbar/trafilatura",
            "capability_id": "html.structure"
          },
          "supply_chain_ledger": {
            "id": "C003",
            "capability": "web-extraction"
          },
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0020",
          "atlas_join_candidates": [
            "CAP-0020"
          ],
          "donor_disposition_archive": [
            "C003"
          ]
        },
        "verification_tier": "A",
        "currently_usable": true,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": "CAP-0020",
        "map_state": "worker_backed",
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "trafilatura",
            "Trafilatura"
          ],
          "hits": {
            "package_declared": {
              "trafilatura": [
                "pyproject.toml:29",
                "pyproject.toml:83",
                "uv.lock:4695"
              ],
              "Trafilatura": [
                "pyproject.toml:29",
                "pyproject.toml:83",
                "uv.lock:4695"
              ]
            },
            "imported_in_source": {
              "trafilatura": [
                "shared/adapter_fixtures.py:117",
                "shared/web_search.py:104",
                "services/python-workers/machine/document_check.py:152"
              ],
              "Trafilatura": [
                "shared/adapter_fixtures.py:117",
                "shared/web_search.py:104",
                "services/python-workers/machine/document_check.py:152"
              ]
            },
            "mentioned_only": {
              "trafilatura": [
                "shared/pipeline.py:105",
                "services/python-workers/README.md:34",
                "services/python-workers/web/worker_webpage.py:15"
              ],
              "Trafilatura": [
                "shared/pipeline.py:105",
                "services/python-workers/README.md:34",
                "services/python-workers/web/worker_webpage.py:15"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": "html.structure",
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "web-extraction"
          ],
          "enableable": true,
          "degrade_reason": null,
          "route_worker_files": [
            "services/python-workers/web/worker_html.py"
          ],
          "named_in_route_worker": true,
          "frontend_only_client": false
        },
        "surface_class": "enableable_plugin",
        "surface_class_reason": "atlas capability CAP-0020 exists, config/capability-map.v1.json state is worker_backed, and package_declared evidence names the donor itself in the declared route html.structure.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "web-extraction",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C003",
        "name": "Trafilatura",
        "version": "2.1.0 (uv.lock and task environment metadata)",
        "canonical_url": "https://github.com/adbar/trafilatura",
        "capability": "web-extraction",
        "code_license": "Apache-2.0",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source"
        ],
        "product_path": "services/python-workers/web/worker_html.py; app/ingestion/multi_format.py; shared/web_search.py",
        "evidence": "Core import/job/execution/output routes run the actual Trafilatura 2.1.0 donor on saved article bytes, suppress nav/footer and persist outputs across Core reopen. Generic snippets or donor failure use recorded stdlib fallback. See OSS-REUSE-VERIFICATION-20261008.json.",
        "decision": "Single article/main static extraction donor; pyproject range is not an installed version. Installed task license file Apache-2.0 SHA256 a6cba85bc92e0cff7a450b1d873c0eaa2e9fc96bf472df0247a26bec77bf3ff9. No network fetch or worker knowledge-store writes.",
        "upstream_note": "Test scope: isolated Windows Core API + Python environment. Packaged/installed desktop and release NOT_RUN.",
        "history": [
          {
            "recorded_at": "2026-10-08",
            "reason": "Current source/result correction; original claim retained, not deleted.",
            "original_record": {
              "id": "C003",
              "name": "Trafilatura",
              "version": ">=1.8 (Apache-2.0)",
              "canonical_url": "https://github.com/adbar/trafilatura",
              "capability": "web-extraction",
              "code_license": "Apache-2.0",
              "model_license": null,
              "disposition": "CURRENT",
              "qualification": [
                "source",
                "installed"
              ],
              "product_path": "app/ingestion/multi_format.py; shared/web_search.py",
              "evidence": "Static HTML baseline extraction",
              "decision": "Must lock to modern Apache-2.0 versions (>=1.8). Older versions were GPL-3.0+. Add source-snapshot evidence.",
              "upstream_note": "License changed at 1.8 from GPL-3.0+ to Apache-2.0. Verify locked version."
            }
          }
        ],
        "current_task_verification": "docs/current/OSS-REUSE-VERIFICATION-20261008.json"
      },
      "qualification": {
        "stable_key": "trafilatura",
        "disposition": "CURRENT_PAGE_SELECTED",
        "reason": "Only this page needs the existing surface; qualification remains separated from runtime availability.",
        "activation": {
          "state": "CURRENT_PAGE_REFERENCE_ONLY",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "UF10/O01 current page"
        },
        "evidence": {
          "version": {
            "state": "LOCK_PINNED",
            "value": {
              "package": "trafilatura",
              "version": "2.1.0",
              "source": {
                "registry": "https://pypi.org/simple"
              },
              "pyproject_range_is_not_version": true
            },
            "source_refs": [
              {
                "path": "uv.lock",
                "sha256": "0e3db03c3dcd71e24acc13022839591b575f10e42f1dbdfde8b86ec77fc8f2e3"
              },
              {
                "path": "pyproject.toml",
                "sha256": "8df2995c350abea2dcb4d8b6f13e80c165abe9d7b2f5ca7d503ace3a6006a63c"
              }
            ]
          },
          "license": {
            "state": "LOCAL_DECLARATION_WITH_OFFICIAL_READBACK",
            "value": {
              "code": "Apache-2.0",
              "weights": "NOT_APPLICABLE",
              "prior_license_file_sha256": "a6cba85bc92e0cff7a450b1d873c0eaa2e9fc96bf472df0247a26bec77bf3ff9",
              "official_sources": [
                "https://github.com/adbar/trafilatura/blob/master/LICENSE"
              ],
              "official_head_is_not_locked_license_hash": true
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-REUSE-VERIFICATION-20261008.json",
                "sha256": "67c25efebac6d42ab4a20e82c27b4f771acaffeafff0a5d913cab38b45ae2cf0"
              },
              {
                "path": "uv.lock",
                "sha256": "0e3db03c3dcd71e24acc13022839591b575f10e42f1dbdfde8b86ec77fc8f2e3"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": "html.structure",
              "enableable_inherited": true,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED",
              "local_saved_input_only": true,
              "knowledge_writer": "Core only",
              "no_new_network_fetch": true
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "A",
              "currently_usable": true,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "weknora",
      "display_names": [
        "WeKnora",
        "Knowledge workspace editing, revision, diff, and rollback UX"
      ],
      "surface_class": "base_dependency",
      "absorption_mode": "UX_DONOR",
      "classification_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "weknora",
        "display_names": [
          "WeKnora",
          "Knowledge workspace editing, revision, diff, and rollback UX"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": null,
          "capability_absorption_registry": {
            "capability_id": "CAP-WEKNORA",
            "absorption_mode": "UX_DONOR",
            "status": "reference"
          },
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "CAP-WEKNORA"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "UX_DONOR",
        "declared_modes": {
          "capability_absorption_registry": "UX_DONOR",
          "capability_absorption_registry_status": "reference",
          "supply_chain_ledger": null,
          "derived_mode": "UX_DONOR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "WeKnora"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": null
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [],
          "enableable": false,
          "degrade_reason": "the absorption registry declares UX_DONOR",
          "frontend_only_client": false
        },
        "surface_class": "base_dependency",
        "surface_class_reason": "this entry names the product itself, not an external donor (registry upstream_project is null or the name is this repository's own declared package/brand). First-party substrate is never an enable-able external source.",
        "conflicts": []
      },
      "ledger": null,
      "qualification": {
        "stable_key": "weknora",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": null,
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "UX_DONOR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": null,
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "whispercpp",
      "display_names": [
        "whisper.cpp"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "SIDECAR",
      "classification_reason": "no single atlas capability joins it: capability ids ['asr-low-resource'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "whispercpp",
        "display_names": [
          "whisper.cpp"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "A006",
            "capability": "asr-low-resource"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A006"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "SIDECAR",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "EVALUATE",
          "derived_mode": "SIDECAR"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "tool_invoked",
          "carried": true,
          "terms": [
            "whisper.cpp"
          ],
          "hits": {
            "tool_invoked": {
              "whisper.cpp": [
                "faster-whisper",
                "faster-whisper-base",
                "shared/bakeoff_engines.py:156",
                "services/python-workers/media/worker_transcribe.py:4"
              ]
            },
            "mentioned_only": {
              "whisper.cpp": [
                "shared/bakeoff_engines.py:190"
              ]
            }
          },
          "bound_resource_entries": [
            "faster-whisper",
            "faster-whisper-base",
            "faster-whisper-large-v3-turbo"
          ],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "MENTIONED_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "asr-low-resource"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['asr-low-resource'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['asr-low-resource'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "declared-non-runtime-but-artifact-is-carried",
            "values": {
              "registry_mode": null,
              "ledger_disposition": "EVALUATE",
              "adoption_artifact": "tool_invoked",
              "hits": {
                "tool_invoked": {
                  "whisper.cpp": [
                    "faster-whisper",
                    "faster-whisper-base",
                    "shared/bakeoff_engines.py:156",
                    "services/python-workers/media/worker_transcribe.py:4"
                  ]
                },
                "mentioned_only": {
                  "whisper.cpp": [
                    "shared/bakeoff_engines.py:190"
                  ]
                }
              }
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "asr-low-resource",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A006",
        "name": "whisper.cpp",
        "canonical_url": "https://github.com/ggml-org/whisper.cpp",
        "capability": "asr-low-resource",
        "code_license": "MIT",
        "model_license": "per-model record required",
        "disposition": "EVALUATE",
        "qualification": [
          "source"
        ],
        "decision": "CPU/quantized/offline ASR alternative. Independent implementation from faster-whisper — use as bake-off partner and low-resource fallback.",
        "upstream_note": "GGML models — each model's license recorded separately."
      },
      "qualification": {
        "stable_key": "whispercpp",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": "per-model record required"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "SIDECAR",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "wikidata",
      "display_names": [
        "Wikidata"
      ],
      "surface_class": "enableable_plugin",
      "absorption_mode": "PYTHON_WORKER",
      "classification_reason": "atlas capability CAP-0030 exists, config/capability-map.v1.json state is core_native, and imported_in_source evidence names the donor itself.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "wikidata",
        "display_names": [
          "Wikidata"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "Wikidata",
            "capability_id": "evidence.wikidata"
          },
          "supply_chain_ledger": {
            "id": "A021",
            "capability": "evidence-entity"
          },
          "capability_absorption_registry": null,
          "capability_atlas": "CAP-0030",
          "atlas_join_candidates": [
            "CAP-0030"
          ],
          "donor_disposition_archive": [
            "A021"
          ]
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "PYTHON_WORKER",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "ADOPT",
          "derived_mode": "PYTHON_WORKER"
        },
        "atlas_capability_id": "CAP-0030",
        "map_state": "core_native",
        "adoption": {
          "artifact": "imported_in_source",
          "carried": true,
          "terms": [
            "Wikidata",
            "wikidata"
          ],
          "hits": {
            "imported_in_source": {
              "Wikidata": [
                "shared/evidence_connectors.py:153",
                "shared/public_evidence.py:17"
              ],
              "wikidata": [
                "shared/evidence_connectors.py:153",
                "shared/public_evidence.py:17"
              ]
            },
            "mentioned_only": {
              "Wikidata": [
                "shared/cross_reference.py:305",
                "shared/oer_crosswalk.py:21",
                "shared/pipeline.py:198"
              ],
              "wikidata": [
                "shared/cross_reference.py:305",
                "shared/oer_crosswalk.py:21",
                "shared/pipeline.py:198"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "IMPLEMENTED_IN_SOURCE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "evidence-entity",
            "evidence.wikidata"
          ],
          "enableable": true,
          "degrade_reason": null,
          "frontend_only_client": false
        },
        "surface_class": "enableable_plugin",
        "surface_class_reason": "atlas capability CAP-0030 exists, config/capability-map.v1.json state is core_native, and imported_in_source evidence names the donor itself.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "evidence-entity",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "evidence.wikidata",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A021",
        "name": "Wikidata",
        "canonical_url": "https://www.wikidata.org/",
        "capability": "evidence-entity",
        "code_license": "CC0 (data)",
        "model_license": null,
        "disposition": "ADOPT",
        "qualification": [
          "source"
        ],
        "decision": "Public entity/identifier/relationship queries. Narrow queries only. User-Agent/429/Retry-After. No fuzzy full-text verification.",
        "upstream_note": "SPARQL/wbgetentities. NOT for full-text search."
      },
      "qualification": {
        "stable_key": "wikidata",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "CC0 (data)",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "PYTHON_WORKER",
              "route": null,
              "enableable_inherited": true,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "xlrd",
      "display_names": [
        "xlrd"
      ],
      "surface_class": "absorbed_algorithm",
      "absorption_mode": "DIRECT_DEPENDENCY",
      "classification_reason": "no single atlas capability joins it: capability ids ['legacy-binary-workbook-reader', 'office.xls'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "xlrd",
        "display_names": [
          "xlrd"
        ],
        "namespaces": {
          "oss_reuse_decision": {
            "canonical_name": "xlrd",
            "capability_id": "office.xls"
          },
          "supply_chain_ledger": {
            "id": "C048",
            "capability": "legacy-binary-workbook-reader"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": null
        },
        "verification_tier": "B",
        "currently_usable": false,
        "absorption_mode": "DIRECT_DEPENDENCY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "CURRENT",
          "derived_mode": "DIRECT_DEPENDENCY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "package_declared",
          "carried": true,
          "terms": [
            "xlrd"
          ],
          "hits": {
            "package_declared": {
              "xlrd": [
                "pyproject.toml:92",
                "uv.lock:5181"
              ]
            },
            "imported_in_source": {
              "xlrd": [
                "services/python-workers/document/worker_office.py:570"
              ]
            },
            "mentioned_only": {
              "xlrd": [
                "services/python-workers/transport/text_ndjson.py:341",
                "crates/archeaxis-application/src/attempts.rs:294",
                "crates/archeaxis-application/tests/office_job_end_to_end.rs:84"
              ]
            }
          },
          "bound_resource_entries": [],
          "direct_declaration": true,
          "ledger_reported_evidence_state": "DECLARED"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": true,
          "undeclared_capability_ids": [
            "legacy-binary-workbook-reader",
            "office.xls"
          ],
          "enableable": false,
          "degrade_reason": "no single atlas capability joins it: capability ids ['legacy-binary-workbook-reader', 'office.xls'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
          "frontend_only_client": false
        },
        "surface_class": "absorbed_algorithm",
        "surface_class_reason": "no single atlas capability joins it: capability ids ['legacy-binary-workbook-reader', 'office.xls'] appear in neither config/capability-map.v1.json runtime_capabilities nor docs/truth/CAPABILITY_ATLAS_V2.yaml dependencies",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "legacy-binary-workbook-reader",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          },
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/current/OSS-REUSE-DECISIONS-20261008.json",
              "capability_id": "office.xls",
              "declared_runtime_capabilities_in_the_same_domain": [
                "office.structure"
              ],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "C048",
        "name": "xlrd",
        "version": "2.0.2",
        "canonical_url": "https://pypi.org/project/xlrd/",
        "capability": "legacy-binary-workbook-reader",
        "code_license": "BSD",
        "model_license": null,
        "disposition": "CURRENT",
        "qualification": [
          "source",
          "installed"
        ],
        "product_path": "services/python-workers/document/worker_office.py",
        "evidence": "declared in the ci-adapters group and pinned in uv.lock; reads the committed project-authored fixture tests/fixtures/golden/golden-xls-anchor.xls through office.structure on this host, and converts each sheet to a declared CSV member the Core imports (crates/archeaxis-application/tests/xls_member_chain.rs). Licence file 3,771 bytes sha256 b5a5dbce60265e305a815a6cb83ed07f24519d8ba644f2a307994488bced8815. FMT-21 real-sample acceptance is NOT_RUN: the fixture is self-authored, not Excel-authored. Qualified to the source and installed tiers only: it is declared in uv.lock, installed in the declared worker environment on this host, and exercised by committed tests; no release artefact contains it, because no release is being made.",
        "decision": "Absorbed as the reader for the BIFF .xls family only; xlrd 2.x cannot read .xlsx, which already has openpyxl. .doc and .ppt stay unnamed in the Core because no reader exists for them here.",
        "upstream_note": "xlrd 2.0.2 supports BIFF versions 2.0 through 8 and accepts either an OLE2 compound document or a raw BIFF stream."
      },
      "qualification": {
        "stable_key": "xlrd",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": "2.0.2",
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "BSD",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "DIRECT_DEPENDENCY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "B",
              "currently_usable": false,
              "ledger": [
                "source",
                "installed"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    },
    {
      "stable_key": "xyflow",
      "display_names": [
        "XYFlow"
      ],
      "surface_class": "future_candidate",
      "absorption_mode": "REFERENCE_ONLY",
      "classification_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
      "declared_runtime_route": null,
      "original_surface": {
        "stable_key": "xyflow",
        "display_names": [
          "XYFlow"
        ],
        "namespaces": {
          "oss_reuse_decision": null,
          "supply_chain_ledger": {
            "id": "A017",
            "capability": "canvas-ui"
          },
          "capability_absorption_registry": null,
          "capability_atlas": null,
          "atlas_join_candidates": [],
          "donor_disposition_archive": [
            "A017"
          ]
        },
        "verification_tier": "D",
        "currently_usable": false,
        "absorption_mode": "REFERENCE_ONLY",
        "declared_modes": {
          "capability_absorption_registry": null,
          "capability_absorption_registry_status": null,
          "supply_chain_ledger": "EVALUATE",
          "derived_mode": "REFERENCE_ONLY"
        },
        "atlas_capability_id": null,
        "map_state": null,
        "adoption": {
          "artifact": "NONE",
          "carried": false,
          "terms": [
            "XYFlow"
          ],
          "hits": {},
          "bound_resource_entries": [],
          "direct_declaration": false,
          "ledger_reported_evidence_state": "NONE"
        },
        "route_binding": {
          "named_route": null,
          "legacy_bound": [],
          "capability_domain_declared": false,
          "undeclared_capability_ids": [
            "canvas-ui"
          ],
          "enableable": false,
          "degrade_reason": "no donor-specific artifact (probed NONE for terms ['XYFlow'])",
          "frontend_only_client": false
        },
        "surface_class": "future_candidate",
        "surface_class_reason": "tier D (the generator's default for a source row with no reviewed verdict) and no donor artifact was found Neither is an adoption.",
        "conflicts": [
          {
            "reason": "capability-id-is-not-a-declared-route",
            "values": {
              "named_by": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "capability_id": "canvas-ui",
              "declared_runtime_capabilities_in_the_same_domain": [],
              "sources": [
                "services/python-workers/routes.json",
                "config/capability-map.v1.json"
              ]
            }
          }
        ]
      },
      "ledger": {
        "id": "A017",
        "name": "XYFlow",
        "canonical_url": "https://github.com/xyflow/xyflow",
        "capability": "canvas-ui",
        "code_license": "MIT",
        "model_license": null,
        "disposition": "EVALUATE",
        "qualification": [
          "source"
        ],
        "decision": "Canvas/Graph visualization. MIT license. File truth remains JSON Canvas. H3 target.",
        "upstream_note": null
      },
      "qualification": {
        "stable_key": "xyflow",
        "disposition": "FROZEN_NOT_SELECTED",
        "reason": "Outside current page selection; original donor intention and conflicts retained, no batch adoption.",
        "activation": {
          "state": "FROZEN",
          "conditions": [
            "Exact capability handshake/readback required before presenting live availability",
            "No install/upgrade/release or remote activation authorization",
            "Retain original conflicts; resolving a name mismatch does not prove installed qualification"
          ],
          "scope": "Deferred outside selected current page"
        },
        "evidence": {
          "version": {
            "state": "UNVERIFIED",
            "value": null,
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "license": {
            "state": "DECLARED_NOT_REQUALIFIED",
            "value": {
              "code": "MIT",
              "weights": null
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "permissions": {
            "state": "DECLARED_INHERITED",
            "value": {
              "absorption_mode": "REFERENCE_ONLY",
              "route": null,
              "enableable_inherited": false,
              "network": "NOT_GRANTED",
              "installation": "NOT_GRANTED",
              "machine_weights": "SEPARATE_TERMS_REQUIRED"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "runtime": {
            "state": "NOT_RUN",
            "value": {
              "live_handshake": "NOT_READ",
              "installed_desktop": "NOT_RUN",
              "release": "NOT_RUN"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              }
            ]
          },
          "qualification": {
            "state": "INHERITED_ONLY",
            "value": {
              "tier": "D",
              "currently_usable": false,
              "ledger": [
                "source"
              ],
              "this_assessment": "READ_ONLY_SOURCE_AND_LOCK"
            },
            "source_refs": [
              {
                "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
                "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
              },
              {
                "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
                "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
              }
            ]
          },
          "source_refs": [
            {
              "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
              "sha256": "013ed5b614ee69e78ec89835570efe11035047cdb83a75d53bde43937c3b53e1"
            },
            {
              "path": "docs/truth/SUPPLY_CHAIN_LEDGER.json",
              "sha256": "91e3da2c2c3771a5fffb1eba8e82fde973308821e0b1d9fd55b0068992642169"
            }
          ]
        }
      }
    }
  ]
};

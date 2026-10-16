/*
  ASTRYN｜星栖 M0 架构模型（C4 / Structurizr DSL）
  真相源：本文件。渲染预览是派生物。
  证据规则：每个节点与每条边都要能追溯到代码路径或 docs/ 下的实测记录；
            未接通项以 BLOCKED 标签保留，不得被读成已实现。
  三类边语义（本项目不可协商）：
    AUTHORITATIVE  宿主回执事件，唯一可改变任务状态
    OBSERVED       会话/输入观测事件，只能改变对话呈现状态
    SYNTHETIC      测试夹具或合成演示，永不构成集成证据
    BLOCKED        宿主合同缺失，当前不可用（不是已实现）
*/

workspace "ASTRYN M0" "星栖 M0：角色化陪伴子系统的可核验架构模型" {

    model {
        owner = person "用户" "星栖的使用者；可暂停、退出并删除与自己相关的数据" "actor"

        aaos = softwareSystem "AAOS" "ArcheAxis Knowledge OS：通用模型、记忆、上下文、任务、权限与权威存储" "external-system" {
            core = container "AAOS Rust Core" "axum loopback HTTP（仅 IPv4、launch token 双凭据、Origin 校验）" "Rust / axum" "external" {
                versionEp = container "system/version" "健康与构建身份" "HTTP GET" "external"
                capEp = container "capabilities" "能力注册表；health 只证明文件存在与协议 hello，不证明引擎" "HTTP GET" "external"
                answersEp = container "machine/answers" "一次性问答（Ollama / LM Studio）。实测无通用流式 chat completion" "HTTP POST" "external,blocked-streaming"
                jobsEp = container "jobs 生命周期" "POST /jobs → /executions（idempotency-key，202=已持久声明非完成）→ status 轮询 → outputs/{kind}（sha256 + authority_effect=candidate_or_measurement_only）" "HTTP" "external,polling-only"
                knowEp = container "knowledge-items" "唯一合法记忆写入口：只产 candidate，晋升永远 human-only" "HTTP POST" "external,candidate-only"
                ctxEp = container "machine/contexts + ai/context-packets" "grant 冻结与恢复围栏；Consumer 为闭集枚举，不含星栖" "HTTP" "external,consumer-closed"
                sqlite = container "SQLite + sha256 CAS" "权威记录与资产（SCHEMA_VERSION 12，Rust 单写者）" "SQLite" "external,datastore"
            }
        }

        upstream = softwareSystem "上游模型提供方" "可选；仅经星栖开发代理访问，凭据不进入浏览器" "external-system"

        astryn = softwareSystem "ASTRYN｜星栖" "AAOS 原生的角色化交互与陪伴子系统，默认角色小栖" "system-of-record-for-character" {

            runtime = container "星栖浏览器运行时" "唯一 M0 可执行体：契约层 + 角色内核 + 呈现层，打成单个前端 bundle" "React 18.3.1 / TypeScript 5.9.3 / Vite 5.4.21" {
                contracts = component "Astryn Contracts" "八类 Port 与事件信封；协议版本 astryn-1；来源×可信矩阵" "TypeScript（不依赖 React）" {
                    hostPort = component "AstrynHostPort" "宿主唯一入口：能力探测、子端口获取、授权申请、权威事件订阅" "interface"
                    convPort = component "AstrynConversationPort" "会话与流式对话端口；自签 source=conversation/trust=observed" "interface"
                    memPort = component "AstrynMemoryPort" "可治理候选记忆契约：作用域/来源/同意/生命周期" "interface"
                    actPort = component "AstrynActionPort" "动作请求、审批与回执；AstrynReceiptVerifier 校验器" "interface"
                    ctxPort = component "AstrynContextPort" "授权上下文与来源标识" "interface"
                    avatarRenderer = component "AstrynAvatarRenderer" "可替换渲染驱动接口（renderer seam）" "interface"
                    presMode = component "AstrynPresentationMode" "embedded/panel/floating/pet/voice-only 声明，仅两种已实现" "interface"
                    charProfile = component "AstrynCharacterProfile" "结构化角色档案（人格/边界/表达/外观），非单块提示词" "interface"
                }
                kernel = component "Astryn Companion Kernel" "角色领域逻辑：状态机、会话守卫、编排、提示组装" "TypeScript" {
                    guard = component "AstrynEventGuard" "会话/请求/序号三重守卫；判别字段缺失与任务权威不足一律拒收并计数" "src/companion/session-guard.ts"
                    reducer = component "reduceCompanionState" "纯 reducer：对话态由用户与流事件驱动；任务态只接受权威回执" "src/companion/reducer.ts"
                    controller = component "AstrynCompanionController" "编排 ports+guard+reducer；构造无副作用，宿主订阅只在 attach() 建立" "src/interaction/companion-controller.ts"
                    composer = component "prompt-composer" "按节组装系统提示，模板版本 xiaoqi-system-1" "src/companion/prompt-composer.ts"
                }
                adapters = component "Astryn Adapters" "宿主与传输适配" "TypeScript" {
                    bridge = component "AaosHostBridge" "按实测端点建模的类型化 Host Adapter；未配置 baseUrl 即返回能力缺失" "src/adapters/aaos-bridge.ts"
                    openai = component "OpenAiCompatibleConversationPort" "仅开发环境标准兼容适配器；经 loopback 代理，浏览器无密钥" "src/adapters/openai-compatible.ts"
                    synth = component "SyntheticConversationPort / SyntheticHostSimulator" "显式标注 SYNTHETIC 的测试与演示夹具" "src/adapters/synthetic-*.ts"
                    registry = component "model-registry" "来源收敛顺序：AAOS → 开发代理 → 显式合成；否则 MODEL_UNAVAILABLE" "src/adapters/model-registry.ts"
                    sse = component "SseDecoder" "跨任意字节边界的 SSE 行解析" "src/adapters/sse.ts"
                }
                memoryCtx = component "Astryn Memory & Context 侧策略" "星栖只持有治理规则与可销毁夹具，不持有主库" "TypeScript" {
                    memPolicy = component "memory/policy" "消费方×作用域禁止表、生命周期迁移判定、虚构不可晋升" "src/memory/policy.ts"
                    memFixture = component "SyntheticMemoryFixture" "进程内 Map，dispose 即清空；不落盘" "src/memory/synthetic-fixture.ts"
                    ctxFixture = component "SyntheticContextFixture" "授权选区夹具；provenance=synthetic-fixture" "src/context/synthetic-context.ts"
                }
                express = component "Astryn Expression & Presentation" "角色表达与可复用 UI" "TypeScript / React / SVG" {
                    renderers = component "avatar-renderers（渲染注册表）" "xiaoqi-raster-v2 九态位图静帧（默认，AI 生成）+ xiaoqi-svg-v1 原创 SVG（回退下限 index 0）；九态视觉映射唯一表；未注册 id 显式回退" "src/avatar/{renderer-registry,xiaoqi-raster-renderer,xiaoqi-svg-renderer}.ts"
                    shell = component "CompanionShell" "embedded/panel 挂载、事件绑定、卸载清理与审计展示" "src/presentation/companion-shell.tsx"
                    view = component "companion-view" "AvatarView / StatusStrip / ChatLog / Composer / ApprovalCard" "src/presentation/companion-view.tsx"
                }
            }

            devhost = container "星栖开发宿主" "独立运行与测试用；不是第二个正式产品前端" "Vite dev server / 127.0.0.1:5183" {
                app = component "DevHostApp" "模式切换、会话切换、来源切换、合成宿主控制、夹具文档与记忆候选面板" "dev-host/app.tsx"
            }

            proxy = container "dev-model-proxy" "仅开发环境的服务端兼容代理：loopback 绑定、单一上游、请求体与超时上限、不回传上游正文" "Node 26 node:http / 127.0.0.1:8791"
        }

        # ---------- 边：用户与呈现 ----------
        owner -> app "启动并观察开发宿主" "HTTP/浏览器" ""
        owner -> shell "看到小栖、输入文本、授权或拒绝动作" "in-process" ""

        # ---------- 边：观测事件（不得改变任务状态）----------
        shell -> controller "提交一轮对话 / 取消 / 聚焦失焦" "in-process" "OBSERVED"
        controller -> composer "按角色档案组装消息" "in-process" "OBSERVED"
        controller -> registry "解析当前模型来源" "in-process" "OBSERVED"
        registry -> openai "选择开发代理端口" "in-process" "OBSERVED"
        registry -> synth "仅在显式允许时选择合成端口" "in-process" "SYNTHETIC"
        openai -> sse "解析流式分块" "in-process" "OBSERVED"
        openai -> proxy "POST /dev-model/v1/chat/completions（无密钥）" "HTTP/SSE" "OBSERVED"
        proxy -> upstream "转发对话请求并回传流" "HTTP/SSE" "OBSERVED"
        controller -> guard "每个事件先过身份与序号守卫" "in-process" "OBSERVED"
        guard -> reducer "仅放行的事件进入 reducer" "in-process " "OBSERVED"
        reducer -> renderers "visibleState + expressionFrame 选择角色帧（位图默认/SVG 回退）" "in-process" "OBSERVED"
        renderers -> shell "产出角色画面（位图加载失败回退 SVG）" "in-process" "OBSERVED"

        # ---------- 边：权威事件（唯一可改变任务状态）----------
        controller -> bridge "获取 conversation/memory/context/actions 子端口与能力探测" "in-process" "AUTHORITATIVE"
        bridge -> core "GET system/version · GET capabilities" "HTTP" "AUTHORITATIVE"
        bridge -> jobsEp "POST /jobs → /executions → 轮询 status → outputs" "HTTP" "AUTHORITATIVE"
        jobsEp -> controller "AstrynActionReceipt（经 verifyReceipt 校验）" "HTTP poll" "AUTHORITATIVE"
        controller -> reducer "仅 trust=authoritative 且 source∈{host-action,host-task} 的任务事件" "in-process" "AUTHORITATIVE"
        synth -> controller "合成宿主回执（authority=synthetic-fixture，界面必须标 SYNTHETIC）" "in-process" "SYNTHETIC"
        bridge -> answersEp "一次性问答映射为单 delta；无流式" "HTTP POST" "BLOCKED"
        bridge -> knowEp "只可提交 candidate；晋升 human-only" "HTTP POST" "BLOCKED"
        bridge -> ctxEp "星栖不在 Consumer 闭集内；无当前选区合同" "HTTP" "BLOCKED"

        # ---------- 边：记忆与上下文治理 ----------
        shell -> memPolicy "查询/登记候选前判定作用域与生命周期" "in-process" "OBSERVED"
        memPolicy -> memFixture "测试与演示走进程内夹具" "in-process" "SYNTHETIC"
        shell -> ctxFixture "请求授权后读取选区（合成文档）" "in-process" "SYNTHETIC"
        memFixture -> sqlite "禁止：星栖不直接写宿主权威存储" "none" "FORBIDDEN"

        # ---------- 边：宿主与运行时承载 ----------
        app -> shell "挂载角色面板（embedded / panel）" "in-process" ""
        runtime -> devhost "在开发宿主内运行" "in-process" ""
        contracts <- kernel "实现并遵守" "in-process" ""
        adapters -> contracts "实现 Port" "in-process" ""
    }

    views {
        systemLandscape "landscape" {
            include *
            autoLayout
            title "星栖 M0 系统全景"
        }

        container astryn "containers" {
            include *
            autoLayout
            title "星栖容器视图：浏览器运行时 · 开发宿主 · loopback 模型代理"
        }

        component runtime "components" {
            include *
            autoLayout
            title "星栖浏览器运行时组件视图"
        }

        styles {
            element "external-system" {
                shape Box
                color #9aa4cf
                background #1b1f38
            }
            element "actor" {
                shape Circle
                background #5ad1c8
            }
            element "system-of-record-for-character" {
                background #16233a
            }
            element "BLOCKED" {
                strokeColor #ff5d5d
                color #ffb3bd
                style Dashed
            }
            element "FORBIDDEN" {
                strokeColor #ff5d5d
                color #ff5d5d
                style Dashed
            }
            element "SYNTHETIC" {
                strokeColor #ffd166
                color #ffd166
            }
            element "datastore" {
                shape Cylinder
            }
            relationship "AUTHORITATIVE" {
                color #63e6a6
                thickness 3
            }
            relationship "OBSERVED" {
                color #7aa2ff
                thickness 1
            }
            relationship "SYNTHETIC" {
                color #ffd166
                style Dashed
            }
            relationship "BLOCKED" {
                color #ff5d5d
                style Dashed
            }
            relationship "FORBIDDEN" {
                color #ff5d5d
                style Dashed
                thickness 4
            }
        }
    }
}

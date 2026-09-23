using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Input.Platform;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using Avalonia.Threading;

namespace ArcheAxis.Desktop;

public partial class MainWindow : Window
{
    private CoreSupervisor? _supervisor;
    private readonly DeepTutorSupervisor _deepTutor = DeepTutorSupervisor.CreateFromEnvironment();
    private string? _activeLearningItem;
    private string? _activeAssessmentId;
    private string? _activeKnowledgeId;
    private string? _activeKnowledgeVersion;
    // One exposure keeps one id pair: a failed submit is retried with the same
    // client_event_id (the Core's idempotency key) and the same exposure_id, so a
    // retry cannot be recorded as a second review. A successful review clears the
    // pair and the next exposure generates fresh ids.
    private string? _activeReviewEventId;
    private string? _activeExposureId;
    private int? _activeReviewRating;
    private string _activeSection = "home";
    private readonly List<string> _sessionJobIds = new();
    private string? _selectedLearningItemKey;
    private bool _hydratingLearningQueue;
    private bool _learningNavigationLoadInProgress;
    private long _sourceReaderRequestVersion;
    private long _sourceTransformRequestVersion;
    private long _evidenceRequestVersion;
    private long _memoryMapRequestVersion;
    private long _learningRequestVersion;
    private long _reviewRequestVersion;
    private long _knowledgeRequestVersion;
    private long _librarySearchRequestVersion;
    private long _machineTaskRequestVersion;
    private long _jobLookupRequestVersion;
    private readonly List<CaptureContextRow> _captureContexts = new();
    private CaptureContextRow? _latestCaptureContext;
    private CaptureContextRow? _selectedCaptureContext;
    private LibraryResultRow? _selectedLibraryResult;
    private bool _returnToLibraryAvailable;
    private bool _knowledgeReturnToLibraryAvailable;
    private string? _librarySearchQuery;
    private string? _activeKnowledgeSourceId;
    private string? _activeEvidenceSourceId;
    private string? _activeMemoryMapSourceId;
    private string? _sourceReaderReturnKnowledgeId;
    private bool _sourceReaderReturnToKnowledgeAvailable;
    private bool _activityDockExpanded;
    private long _workspaceSummaryRequestVersion;
    private bool _homeLearningAvailable;
    private int? _homeLearningCount;
    private bool _inspectorDrawerOpen;
    private bool _reducedMotion;
    private DispatcherTimer? _homeHeroAmbientTimer;
    private bool _homeHeroAmbientBright;
    private IInputElement? _commandPaletteReturnFocus;
    private readonly DispatcherTimer _toastTimer = new() { Interval = TimeSpan.FromMilliseconds(2600) };
    private sealed record CommandPaletteRoute(
        string Label,
        string Section,
        string Heading,
        params string[] Aliases)
    {
        public bool Matches(string command) =>
            string.Equals(command, Label, StringComparison.OrdinalIgnoreCase)
            || Aliases.Any(alias => string.Equals(command, alias, StringComparison.OrdinalIgnoreCase));
    }

    private static readonly CommandPaletteRoute[] CommandPaletteRoutes =
    {
        new("首页", "home", "首页", "工作台"),
        new("捕获", "capture", "捕获", "Capture"),
        new("资料库", "library", "资料库", "资料与知识"),
        new("原件阅读", "source-reader", "导入阅读", "导入阅读"),
        new("知识库", "knowledge", "知识库", "知识详情"),
        new("原件编辑", "original-editor", "原件编辑", "编辑原件"),
        new("记忆地图", "memory-map", "记忆地图", "Memory Map", "记忆图谱"),
        new("学习", "learning", "学习", "学习路径"),
        new("证据中心", "evidence", "证据中心"),
        new("研究", "research", "研究"),
        new("机器知识", "machine-growth", "机器知识"),
        new("任务", "jobs", "任务", "任务收据"),
        new("插件", "plugins", "插件"),
        new("模型", "models", "模型"),
        new("恢复", "recovery", "恢复"),
        new("设置", "settings", "设置", "系统"),
    };

    private static readonly string[] CommandPaletteCommands = CommandPaletteRoutes
        .SelectMany(route => new[] { route.Label }.Concat(route.Aliases))
        .Distinct(StringComparer.OrdinalIgnoreCase)
        .ToArray();

    public sealed class CaptureContextRow
    {
        public string FileName { get; }
        public string SourceId { get; }
        public string JobId { get; set; }
        public string JobState { get; set; }
        public string DisplayText =>
            $"文件：{FileName}\nsource_id={SourceId}\njob_id={JobId}\n状态={JobState}";

        public CaptureContextRow(string fileName, string sourceId)
        {
            FileName = fileName;
            SourceId = sourceId;
            JobId = "未提交";
            JobState = "source_received";
        }

        public override string ToString() => DisplayText;
    }

    public sealed class SourceMemberRow
    {
        public string SourceId { get; }
        public string Member { get; }
        public string OriginalName { get; }
        public string Sha256 { get; }
        public string Readable { get; }
        public string JobId { get; }
        public string DisplayText => $"{(string.IsNullOrWhiteSpace(OriginalName) ? Member : OriginalName)} · readable={Readable} · job={JobId}";

        public SourceMemberRow(string sourceId, string member, string originalName, string sha256, string readable, string jobId)
        {
            SourceId = sourceId;
            Member = member;
            OriginalName = originalName;
            Sha256 = sha256;
            Readable = readable;
            JobId = jobId;
        }

        public override string ToString() => DisplayText;
    }

    public sealed class JobReceiptRow
    {
        public string JobId { get; }
        public string State { get; }
        public string SemanticState { get; }
        public string Detail { get; }
        public string DisplayText => $"{JobId} · {State}";

        public JobReceiptRow(string jobId, string state, string detail, string semanticState)
        {
            JobId = jobId;
            State = state;
            Detail = detail;
            SemanticState = semanticState;
        }

        public override string ToString() => Detail;
    }

    public sealed class LearningQueueRow
    {
        public string ItemKey { get; }
        public string NextReview { get; }
        public string DisplayText => $"{ItemKey} · 下次复习：{NextReview}";

        public LearningQueueRow(string itemKey, string nextReview)
        {
            ItemKey = itemKey;
            NextReview = nextReview;
        }

        public override string ToString() => DisplayText;
    }

    public MainWindow()
    {
        InitializeComponent();
        AttachAccessibleTextSync(CoreStatusText);
        AttachAccessibleTextSync(FirstRunCoreStatusText);
        AttachAccessibleTextSync(FirstRunWorkspaceStatusText);
        AttachAccessibleTextSync(FirstRunOptionalStatusText);
        AttachAccessibleTextSync(HomeFocusText);
        AttachAccessibleTextSync(HomeEvidenceText);
        AttachAccessibleTextSync(HomeLifecycleCaptureText);
        AttachAccessibleTextSync(HomeLifecycleSourceText);
        AttachAccessibleTextSync(HomeLifecycleKnowledgeText);
        AttachAccessibleTextSync(HomeLifecycleLearningText);
        AttachAccessibleTextSync(HomeLifecycleReviewText);
        AttachAccessibleTextSync(SettingsCoreStatusText);
        AttachAccessibleTextSync(SettingsWorkspaceStatusText);
        Title = "ArcheAxis Learning Workspace (vNext) — core offline";
        _reducedMotion = string.Equals(Environment.GetEnvironmentVariable("AAOS_REDUCED_MOTION"), "1", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Environment.GetEnvironmentVariable("AAOS_REDUCED_MOTION"), "true", StringComparison.OrdinalIgnoreCase);
        if (_reducedMotion)
        {
            MainFrameGrid.Classes.Set("reduced-motion", true);
        }
        Loaded += OnLoaded;
        Closed += OnClosed;
        _toastTimer.Tick += OnToastTimerTick;
    }

    private static void AttachAccessibleTextSync(TextBlock target)
    {
        Avalonia.Automation.AutomationProperties.SetName(target, target.Text ?? string.Empty);
        target.PropertyChanged += (_, args) =>
        {
            if (args.Property == TextBlock.TextProperty)
                Avalonia.Automation.AutomationProperties.SetName(target, target.Text ?? string.Empty);
        };
    }

    private async void OnLoaded(object? sender, RoutedEventArgs e)
    {
        StartHomeHeroAmbientMotion();
        // Only start and authenticate our own Core; never adopt a shared service.
        FirstRunCoreStatusText.Text = "Core：正在启动检查";
        var dbPath = Environment.GetEnvironmentVariable("ARCHEAXIS_VNEXT_DB")
            ?? Environment.GetEnvironmentVariable("ARCHAXIS_VNEXT_DB")
            ?? System.IO.Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "ArcheAxis", "vnext", "workspace.sqlite");
        CoreTextWorker? worker;
        try
        {
            worker = WorkerProfile.Load(AppContext.BaseDirectory,
                Environment.GetEnvironmentVariable("ARCHEAXIS_WORKER_PROFILE")
                    ?? Environment.GetEnvironmentVariable("ARCHAXIS_WORKER_PROFILE"));
        }
        catch (Exception)
        {
            Title = "星环知识平台 — 工作组件配置无效，请检查运行配置";
            CoreStatusText.Text = "核心状态：配置无效";
            FirstRunCoreStatusText.Text = "Core：工作组件配置无效";
            FirstRunOptionalStatusText.Text = "可选能力：文本处理组件配置无效；插件、模型、Sidecar 未接入权威 readiness 投影。";
            CoreStatusText.Classes.Set("status-success", false);
            CoreStatusText.Classes.Set("status-error", true);
            return;
        }
        _supervisor = new CoreSupervisor(dbPath, textWorker: worker);
        var result = await _supervisor.StartAsync();
        if (result.ok)
        {
            var connectedTitle = worker is null ? "星环知识平台 — 文本处理组件未配置"
                : "星环知识平台 — 已连接";
            Title = connectedTitle;
            CoreStatusText.Text = worker is null ? "核心状态：已连接 · 未配置文本组件"
                : "核心状态：已连接";
            FirstRunCoreStatusText.Text = "Core：已连接";
            FirstRunOptionalStatusText.Text = worker is null
                ? "文本处理组件：未配置；插件、模型、Sidecar 未接入权威 readiness 投影。"
                : "文本处理组件：已提供给本次 Core 启动；插件、模型、Sidecar 未接入权威 readiness 投影。";
            CoreStatusText.Classes.Set("status-success", result.ok);
            CoreStatusText.Classes.Set("status-error", !result.ok);
            await RefreshWorkspaceSummaryAsync();
        }
        else
        {
            Title = $"ArcheAxis Learning Workspace (vNext) — core offline ({result.detail})";
            CoreStatusText.Text = "核心状态：离线";
            FirstRunCoreStatusText.Text = "Core：离线";
            FirstRunWorkspaceStatusText.Text = "工作区：Core 未连接，未读取工作区状态";
            CoreStatusText.Classes.Set("status-success", result.ok);
            CoreStatusText.Classes.Set("status-error", !result.ok);
        }
    }

    private async Task RefreshWorkspaceSummaryAsync()
    {
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
            return;
        var requestVersion = ++_workspaceSummaryRequestVersion;
        try
        {
            using var response = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/workspaces/info");
            int? sources = null;
            int? anchors = null;
            if (response.IsSuccessStatusCode)
            {
                using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
                sources = ReadOptionalInt(document.RootElement, "sources");
                anchors = ReadOptionalInt(document.RootElement, "anchors");
                FirstRunWorkspaceStatusText.Text = sources is null || anchors is null
                    ? "工作区：Core 已连接，但 sources/anchors 字段未完整暴露。"
                    : $"工作区：Core 已返回真实状态 · 来源 {sources} · 锚点 {anchors}";
                SourcesCountText.Text = FormatOptionalCount(sources);
                AnchorsCountText.Text = FormatOptionalCount(anchors);
            }
            else
            {
                FirstRunWorkspaceStatusText.Text = $"工作区：Core 摘要不可用（HTTP {(int)response.StatusCode}）；当前值未保留。";
                SourcesCountText.Text = "—";
                AnchorsCountText.Text = "—";
            }

            using var learningResponse = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/learning/items");
            var learning = (int?)null;
            var learningAvailable = learningResponse.IsSuccessStatusCode;
            if (learningAvailable)
            {
                using var learningDocument = JsonDocument.Parse(await learningResponse.Content.ReadAsStringAsync());
                learning = ReadOptionalInt(learningDocument.RootElement, "count");
                HomeFocusText.Text = learning is null
                    ? "Core 学习队列已连接，但 count 字段未暴露。"
                    : learning > 0
                    ? $"Core 当前有 {learning} 个待学习项目；可从学习路径继续。"
                    : "Core 当前没有待学习项目。";
            }
            else
            {
                HomeFocusText.Text = "Core 学习队列暂不可用。";
            }
            if (requestVersion != _workspaceSummaryRequestVersion)
                return;
            _homeLearningAvailable = learningAvailable;
            _homeLearningCount = learning;
            HomeFocusLearningButton.IsEnabled = learningAvailable;
            LearningCountText.Text = learningAvailable ? FormatOptionalCount(learning) : "—";
            RefreshHomeLifecycleProjection();
        }
        catch (Exception)
        {
            CoreStatusText.Text = "核心状态：已连接 · 状态读取失败";
            FirstRunWorkspaceStatusText.Text = "工作区：状态读取失败；未推断为可用";
            SourcesCountText.Text = "—";
            AnchorsCountText.Text = "—";
            _homeLearningAvailable = false;
            _homeLearningCount = null;
            HomeFocusLearningButton.IsEnabled = false;
            LearningCountText.Text = "—";
            RefreshHomeLifecycleProjection();
        }
    }

    private static int? ReadOptionalInt(JsonElement root, string name)
    {
        return root.TryGetProperty(name, out var value) && value.TryGetInt32(out var count)
            ? count
            : null;
    }

    private static string FormatOptionalCount(int? value) => value?.ToString() ?? "—";

    private static int ReadInt(JsonElement root, string name) => ReadOptionalInt(root, name) ?? 0;

    private void RefreshHomeLifecycleProjection()
    {
        var context = _selectedCaptureContext ?? _latestCaptureContext;
        HomeLifecycleCaptureText.Text = context is null
            ? "empty · 尚无当前会话来源"
            : "received · 当前会话已登记 source_id";
        HomeLifecycleSourceText.Text = context is null
            ? "unavailable · 尚未登记来源"
            : context.JobState is "queued" or "running"
                ? $"processing · {context.JobState}"
                : context.JobState is "succeeded" or "completed"
                    ? $"available · {context.JobState}"
                    : context.JobState is "failed" or "error" or "cancelled"
                        ? $"error · {context.JobState}；请从来源阅读重试"
                        : $"unknown · {context.JobState}；未推断为可用";
        HomeLifecycleKnowledgeText.Text = "unavailable · Home 未建立 knowledge_id 关联";
        HomeLifecycleLearningText.Text = !_homeLearningAvailable
            ? "unavailable · Core 队列不可用"
            : _homeLearningCount is null
                ? "unavailable · count 字段未暴露"
                : _homeLearningCount > 0
                    ? $"available · {_homeLearningCount} 项"
                    : "empty · 无待学习项目";
        HomeLifecycleReviewText.Text = "unavailable · Home 未读取 due-review";
    }

    private void SetSection(string section, string heading)
    {
        if (!string.Equals(section, "machine-growth", StringComparison.Ordinal))
            ++_machineTaskRequestVersion;
        if (!string.Equals(section, "jobs", StringComparison.Ordinal))
            ++_jobLookupRequestVersion;
        _activeSection = section;
        WorkspaceHeadingText.Text = heading;
        Avalonia.Automation.AutomationProperties.SetName(WorkspaceHeadingText, heading);
        Dispatcher.UIThread.Post(() => WorkspaceHeadingText.Focus(), DispatcherPriority.Input);
        InspectorSectionText.Text = heading;
        InspectorObjectText.Text = "未选择对象";
        InspectorDetailsText.Text = "对象来源、版本和证据将在选择具体对象后显示。";
        InspectorSourceText.Text = "未暴露";
        InspectorVersionText.Text = "未暴露";
        InspectorStatusText.Text = "未暴露";
        InspectorBoundaryText.Text = "字段缺失不推断";
        InspectorLayerText.Text = "Core projection · 类型未暴露";
        InspectorChainSourceText.Text = "来源 → 未暴露";
        InspectorChainVersionText.Text = "版本 → 未暴露";
        InspectorChainProjectionText.Text = "当前投影 → 未暴露";
        InspectorProvenanceText.Text = "未选择对象；来源链未加载。";
        ResetInspectorActions();
        var railSpace = section switch
        {
            "capture" => "capture",
            "source-reader" => "reader",
            "library" or "knowledge" => "knowledge",
            "original-editor" or "memory-map" => "knowledge",
            "learning" => "learning",
            "evidence" => "evidence",
            "machine-growth" => "machine",
            "research" => "research",
            "jobs" => "jobs",
            "plugins" => "plugins",
            "models" => "models",
            "recovery" or "settings" => "system",
            _ => "workspace",
        };
        RailWorkspaceButton.Classes.Set("active", railSpace == "workspace");
        RailCaptureButton.Classes.Set("active", railSpace == "capture");
        RailKnowledgeButton.Classes.Set("active", railSpace == "knowledge");
        RailReaderButton.Classes.Set("active", railSpace == "reader");
        RailLearningButton.Classes.Set("active", railSpace == "learning");
        RailEvidenceButton.Classes.Set("active", railSpace == "evidence");
        RailMachineButton.Classes.Set("active", railSpace == "machine");
        RailResearchButton.Classes.Set("active", railSpace == "research");
        RailJobsButton.Classes.Set("active", railSpace == "jobs");
        RailPluginsButton.Classes.Set("active", railSpace == "plugins");
        RailModelsButton.Classes.Set("active", railSpace == "models");
        RailSystemButton.Classes.Set("active", railSpace == "system");
        MobileWorkspaceButton.Classes.Set("active", railSpace == "workspace");
        MobileCaptureButton.Classes.Set("active", railSpace == "capture");
        MobileKnowledgeButton.Classes.Set("active", railSpace == "knowledge");
        MobileReaderButton.Classes.Set("active", railSpace == "reader");
        MobileLearningButton.Classes.Set("active", railSpace == "learning");
        MobileEvidenceButton.Classes.Set("active", railSpace == "evidence");
        MobileMachineButton.Classes.Set("active", railSpace == "machine");
        MobileResearchButton.Classes.Set("active", railSpace == "research");
        MobileJobsButton.Classes.Set("active", railSpace == "jobs");
        MobilePluginsButton.Classes.Set("active", railSpace == "plugins");
        MobileModelsButton.Classes.Set("active", railSpace == "models");
        MobileSystemButton.Classes.Set("active", railSpace == "system");
        HomeSurface.IsVisible = section == "home";
        CaptureSurface.IsVisible = section == "capture";
        LibrarySurface.IsVisible = section == "library";
        SourceReaderSurface.IsVisible = section == "source-reader";
        KnowledgeSurface.IsVisible = section == "knowledge";
        LearningSurface.IsVisible = section == "learning";
        EvidenceSurface.IsVisible = section == "evidence";
        MemoryMapSurface.IsVisible = section == "memory-map";
        MachineKnowledgeSurface.IsVisible = section == "machine-growth";
        RecoverySurface.IsVisible = section == "recovery";
        SettingsSurface.IsVisible = section == "settings";
        JobsSurface.IsVisible = section == "jobs";
        HomeStatsSurface.IsVisible = section == "home";
        ContextWorkspaceSubnav.IsVisible = section == "home";
        ContextCaptureSubnav.IsVisible = section == "capture";
        ContextKnowledgeSubnav.IsVisible = section is "library" or "source-reader" or "knowledge" or "original-editor" or "memory-map";
        ContextLearningSubnav.IsVisible = section == "learning";
        ContextMachineSubnav.IsVisible = section == "machine-growth";
        ContextSystemSubnav.IsVisible = section is "jobs" or "recovery" or "settings";
        UnavailableSurface.IsVisible = section is "research" or "plugins" or "models" or "original-editor";
        if (UnavailableSurface.IsVisible)
        {
            UnavailableSurfaceTitle.Text = $"{heading} · 尚未接入 Core";
            UnavailableSurfaceStateText.Text = "状态 · Core contract unavailable";
            UnavailableSurfaceBoundaryText.Text = "当前界面保持只读；不创建合成数据、随机状态或第二套真相。";
            UnavailableSurfaceText.Text = section switch
            {
                "research" => "此页面尚未接入 Core 的研究任务、来源或结论投影；不创建或展示合成研究状态。",
                "plugins" => "此页面尚未接入权威插件注册表；不展示已安装、启用、默认/回退或健康状态，也不提供管理操作。",
                "models" => "此页面尚未接入 Core 模型注册表或配置投影；不展示可用模型、活动提供方或健康状态，也不修改模型配置。",
                "original-editor" => "当前 Core 只暴露来源成员与转换读取边界；原件编辑持久化和版本提交接口尚未接入，不在桌面侧创建第二写入路径。",
                "recovery" => "此页面尚未接入 Core 的备份与恢复投影；不展示恢复点，不执行、预演或模拟恢复，也不表示数据可恢复。",
                _ => "该工作区尚未接入 Core 读模型。",
            };
            UnavailableSurfaceNextStepText.Text = section switch
            {
                "research" => "接入带来源与版本绑定的 Research read model。",
                "plugins" => "接入权威 Plugin Registry 与 readiness projection。",
                "models" => "接入 Core Model Registry 与 provider health projection。",
                "original-editor" => "等待 Core 原件编辑、版本提交与冲突处理契约。",
                "recovery" => "等待 Core 备份/恢复投影与 owner-gated 执行契约。",
                _ => "需要对应的 Core 读模型或写入契约。",
            };
        }
        if (section == "jobs")
        {
            _ = RefreshJobsAsync();
        }
        else if (section == "evidence")
        {
            _ = RefreshEvidenceAsync();
        }
        else if (section == "memory-map")
        {
            _ = RefreshMemoryMapAsync();
        }
        else if (section == "settings")
        {
            _ = RefreshSettingsAsync();
        }
        else if (section == "learning" && !_learningNavigationLoadInProgress)
        {
            _ = LoadLearningIfNeededAsync();
        }
        else if (section == "recovery")
        {
            _ = ReadRecoveryStatusAsync();
        }
        PlayWorkspaceRouteTransition();
        if (section == "home")
            StartHomeHeroAmbientMotion();
        else
            StopHomeHeroAmbientMotion();
        BackToKnowledgeFromSourceButton.IsEnabled = section == "source-reader" && _sourceReaderReturnToKnowledgeAvailable;
        RefreshInspectorAccessibleNames();
        UpdateInspectorActions();
    }

    private void PlayWorkspaceRouteTransition()
    {
        if (_reducedMotion)
        {
            WorkspaceScrollViewer.Opacity = 1;
            return;
        }
        WorkspaceScrollViewer.Opacity = 0.78;
        Dispatcher.UIThread.Post(() => WorkspaceScrollViewer.Opacity = 1, DispatcherPriority.Render);
    }

    private void StartHomeHeroAmbientMotion()
    {
        if (_reducedMotion)
        {
            HomeHeroAmbientGlow.Opacity = 0.14;
            return;
        }
        _homeHeroAmbientTimer ??= new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(GetAaosBreakpoint("AaosMotionAmbientMs", 4200)),
        };
        _homeHeroAmbientTimer.Tick -= OnHomeHeroAmbientTick;
        _homeHeroAmbientTimer.Tick += OnHomeHeroAmbientTick;
        HomeHeroAmbientGlow.Opacity = 0.14;
        _homeHeroAmbientBright = false;
        _homeHeroAmbientTimer.Start();
    }

    private void StopHomeHeroAmbientMotion()
    {
        _homeHeroAmbientTimer?.Stop();
        HomeHeroAmbientGlow.Opacity = 0.14;
        _homeHeroAmbientBright = false;
    }

    private void OnHomeHeroAmbientTick(object? sender, EventArgs e)
    {
        if (_reducedMotion || !HomeSurface.IsVisible)
        {
            StopHomeHeroAmbientMotion();
            return;
        }
        _homeHeroAmbientBright = !_homeHeroAmbientBright;
        HomeHeroAmbientGlow.Opacity = _homeHeroAmbientBright ? 0.22 : 0.14;
    }

    private static string DisplayInspectorValue(string? value) =>
        string.IsNullOrWhiteSpace(value) || value == "—" ? "未暴露" : value;

    private static bool HasProvenanceValue(string? value) =>
        !string.IsNullOrWhiteSpace(value) && value != "—";

    private void SetInspectorProjection(
        string objectName,
        string details,
        string? source = null,
        string? version = null,
        string? status = null,
        string boundary = "字段缺失不推断",
        string layer = "Core projection · 类型未暴露")
    {
        InspectorObjectText.Text = objectName;
        InspectorDetailsText.Text = details;
        InspectorSourceText.Text = DisplayInspectorValue(source);
        InspectorVersionText.Text = DisplayInspectorValue(version);
        InspectorStatusText.Text = DisplayInspectorValue(status);
        InspectorBoundaryText.Text = boundary;
        InspectorLayerText.Text = layer;
        InspectorChainSourceText.Text = $"来源 → {DisplayInspectorValue(source)}";
        InspectorChainVersionText.Text = $"版本 → {DisplayInspectorValue(version)}";
        InspectorChainProjectionText.Text = $"当前投影 → {DisplayInspectorValue(objectName)}";
        InspectorProvenanceText.Text = "来自受控 Core projection；字段缺失不推断。";
        RefreshInspectorAccessibleNames();
    }

    private void RefreshInspectorAccessibleNames()
    {
        Avalonia.Automation.AutomationProperties.SetName(InspectorSectionText, InspectorSectionText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorObjectText, InspectorObjectText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorDetailsText, InspectorDetailsText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorSourceText, InspectorSourceText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorVersionText, InspectorVersionText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorStatusText, InspectorStatusText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorBoundaryText, InspectorBoundaryText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorLayerText, InspectorLayerText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorChainSourceText, InspectorChainSourceText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorChainVersionText, InspectorChainVersionText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorChainProjectionText, InspectorChainProjectionText.Text ?? string.Empty);
        Avalonia.Automation.AutomationProperties.SetName(InspectorProvenanceText, InspectorProvenanceText.Text ?? string.Empty);
    }

    private void ResetInspectorActions()
    {
        InspectorOpenSourceButton.IsEnabled = false;
        InspectorOpenKnowledgeButton.IsEnabled = false;
        InspectorBackLibraryButton.IsEnabled = false;
    }

    private void UpdateInspectorActions()
    {
        var hasKnowledgeSource = KnowledgeSurface.IsVisible
            && !string.IsNullOrWhiteSpace(_activeKnowledgeSourceId)
            && _activeKnowledgeSourceId != "—";
        var hasEvidenceSource = EvidenceSurface.IsVisible
            && !string.IsNullOrWhiteSpace(_activeEvidenceSourceId)
            && _activeEvidenceSourceId != "—";
        var hasMemoryMapSource = MemoryMapSurface.IsVisible
            && !string.IsNullOrWhiteSpace(_activeMemoryMapSourceId)
            && _activeMemoryMapSourceId != "—";
        var hasLibraryResult = LibrarySurface.IsVisible && _selectedLibraryResult is not null;
        InspectorOpenSourceButton.IsEnabled = hasKnowledgeSource
            || hasEvidenceSource
            || hasMemoryMapSource
            || (hasLibraryResult && !string.IsNullOrWhiteSpace(_selectedLibraryResult!.SourceId) && _selectedLibraryResult.SourceId != "—");
        InspectorOpenKnowledgeButton.IsEnabled = (hasLibraryResult
            && _selectedLibraryResult!.Kind == "knowledge"
            && !string.IsNullOrWhiteSpace(_selectedLibraryResult.KnowledgeId))
            || (SourceReaderSurface.IsVisible && _sourceReaderReturnToKnowledgeAvailable);
        InspectorBackLibraryButton.IsEnabled = _knowledgeReturnToLibraryAvailable || _returnToLibraryAvailable;
    }

    private void OnInspectorOpenSourceClick(object? sender, RoutedEventArgs e)
    {
        if (KnowledgeSurface.IsVisible)
            OnOpenKnowledgeSourceClick(sender, e);
        else if (EvidenceSurface.IsVisible)
            OnOpenEvidenceSourceClick(sender, e);
        else if (MemoryMapSurface.IsVisible)
            OnOpenMemoryMapSourceClick(sender, e);
        else if (LibrarySurface.IsVisible)
            OnOpenLibrarySourceClick(sender, e);
    }

    private void OnInspectorOpenKnowledgeClick(object? sender, RoutedEventArgs e)
    {
        if (SourceReaderSurface.IsVisible)
            OnBackToKnowledgeFromSourceClick(sender, e);
        else
            OnOpenSelectedKnowledgeClick(sender, e);
    }

    private void OnInspectorBackLibraryClick(object? sender, RoutedEventArgs e)
    {
        if (KnowledgeSurface.IsVisible)
            OnBackToLibraryFromKnowledgeClick(sender, e);
        else if (SourceReaderSurface.IsVisible)
        {
            if (_knowledgeReturnToLibraryAvailable)
                OnBackToLibraryFromKnowledgeClick(sender, e);
            else
                OnBackToLibraryClick(sender, e);
        }
    }

    private void SetStatus(TextBlock target, string text, string semanticState)
    {
        foreach (var state in new[] { "status-success", "status-error", "status-info", "status-review", "status-loading", "status-empty", "status-permission", "status-version", "status-unknown", "status-disabled", "status-warning" })
            target.Classes.Set(state, false);
        target.Classes.Set("status-success", semanticState == "success");
        target.Classes.Set("status-error", semanticState == "error");
        target.Classes.Set("status-info", semanticState == "info");
        target.Classes.Set("status-review", semanticState == "needs-review");
        target.Classes.Set("status-loading", semanticState == "loading");
        target.Classes.Set("status-empty", semanticState == "empty");
        target.Classes.Set("status-permission", semanticState == "permission");
        target.Classes.Set("status-version", semanticState == "version");
        target.Classes.Set("status-unknown", semanticState == "unknown");
        target.Classes.Set("status-disabled", semanticState == "unavailable" || semanticState == "disabled");
        target.Classes.Set("status-warning", semanticState == "warning");
        target.Text = text;
        Avalonia.Automation.AutomationProperties.SetName(target, text);
        Avalonia.Automation.AutomationProperties.SetLiveSetting(
            target,
            semanticState is "error" or "permission"
                ? Avalonia.Automation.AutomationLiveSetting.Assertive
                : Avalonia.Automation.AutomationLiveSetting.Polite);
    }

    private void SetActivityDockSummary(string text)
    {
        ActivityDockText.Text = text;
        Avalonia.Automation.AutomationProperties.SetName(ActivityDockText, text);
    }

    private void SetActivityDockDetails(string text)
    {
        ActivityDockDetailsText.Text = text;
        Avalonia.Automation.AutomationProperties.SetName(ActivityDockDetailsText, text);
    }

    private void ShowToast(string message, string semanticState = "success")
    {
        SetStatus(ToastText, message, semanticState);
        foreach (var state in new[] { "toast-success", "toast-error", "toast-info", "toast-review", "toast-warning" })
            ToastSurface.Classes.Set(state, false);
        var toastState = semanticState switch
        {
            "error" => "toast-error",
            "info" or "loading" => "toast-info",
            "needs-review" or "permission" => "toast-review",
            "warning" => "toast-warning",
            _ => "toast-success",
        };
        ToastSurface.Classes.Set(toastState, true);
        RevealSurface(ToastSurface);
        _toastTimer.Stop();
        _toastTimer.Start();
    }

    private void OnToastTimerTick(object? sender, EventArgs e)
    {
        _toastTimer.Stop();
        ToastSurface.Opacity = 1;
        ToastSurface.IsVisible = false;
    }

    private void RevealSurface(Control target)
    {
        target.IsVisible = true;
        if (_reducedMotion)
        {
            target.Opacity = 1;
            return;
        }

        target.Opacity = 0;
        Dispatcher.UIThread.Post(() =>
        {
            if (target.IsVisible)
                target.Opacity = 1;
        });
    }

    private static bool IsPermissionStatus(System.Net.HttpStatusCode statusCode)
        => statusCode is System.Net.HttpStatusCode.Unauthorized
            or System.Net.HttpStatusCode.Forbidden;

    private static string JobStateSemantic(string state)
        => state switch
        {
            "queued" or "running" => "loading",
            "succeeded" or "completed" => "success",
            "failed" or "error" or "cancelled" => "error",
            _ => "unknown",
        };

    private void OnToggleInspectorDrawerClick(object? sender, RoutedEventArgs e)
    {
        _inspectorDrawerOpen = !_inspectorDrawerOpen;
        if (_inspectorDrawerOpen)
            RevealSurface(InspectorPanel);
        else
        {
            InspectorPanel.Opacity = 1;
            InspectorPanel.IsVisible = false;
        }
        var label = _inspectorDrawerOpen ? "关闭证据检查器" : "打开证据检查器";
        InspectorDrawerButton.Content = label;
        Avalonia.Automation.AutomationProperties.SetName(InspectorDrawerButton, label);
        if (_inspectorDrawerOpen)
            InspectorPanel.Focus();
    }

    private void ResetLearningProjectionForUnavailable(string reason, string action)
    {
        _activeLearningItem = null;
        _activeReviewEventId = null;
        _activeExposureId = null;
        _activeAssessmentId = null;
        _activeKnowledgeId = null;
        _activeKnowledgeVersion = null;
        _activeReviewRating = null;

        LearningItemText.Text = $"{reason}\n{action}";
        LearningEvidenceText.Text = "未载入 Core 学习来源；不保留上一条学习来源。";
        LearningOriginalText.Text = "原件正文未读取。";
        LearningVersionText.Text = "knowledge_id=未读取\nknowledge_version=未生成\nassessment_id=未生成";
        LearningMemoryText.Text = "学习记录：未读回。";
        LearningReviewReceiptText.Text = "排程、下一次复习和 Mastery projection：未读取。";
        LearningAnswerBox.Text = string.Empty;
        LearningAnswerBox.IsEnabled = false;
        ReviewOutcomeBox.SelectedIndex = 0;
        ReviewOutcomeBox.IsEnabled = false;
        ReviewAgainButton.IsEnabled = false;
        ReviewHardButton.IsEnabled = false;
        ReviewGoodButton.IsEnabled = false;
        ReviewEasyButton.IsEnabled = false;
        SubmitReviewButton.IsEnabled = false;
        OpenLearningKnowledgeButton.IsEnabled = false;
        LearningEmptyActions.IsVisible = false;
        ReviewAgainButton.Classes.Set("selected", false);
        ReviewHardButton.Classes.Set("selected", false);
        ReviewGoodButton.Classes.Set("selected", false);
        ReviewEasyButton.Classes.Set("selected", false);
    }

    private void FinishLearningRequest(long requestVersion)
    {
        if (requestVersion != _learningRequestVersion)
            return;
        LoadLearningButton.IsEnabled = true;
    }

    private void OnHomeClick(object? sender, RoutedEventArgs e) => SetSection("home", "首页");

    private void OnCaptureClick(object? sender, RoutedEventArgs e) => SetSection("capture", "捕获");

    private void OnLibraryClick(object? sender, RoutedEventArgs e)
    {
        _selectedLibraryResult = null;
        _librarySearchQuery = null;
        _returnToLibraryAvailable = false;
        _knowledgeReturnToLibraryAvailable = false;
        _activeKnowledgeSourceId = null;
        SetSection("library", "资料库");
    }

    private void OnSourceReaderClick(object? sender, RoutedEventArgs e)
    {
        _sourceReaderReturnToKnowledgeAvailable = false;
        _sourceReaderReturnKnowledgeId = null;
        _returnToLibraryAvailable = false;
        _knowledgeReturnToLibraryAvailable = false;
        BackToLibraryButton.IsEnabled = false;
        SetSection("source-reader", "导入阅读");
    }

    private void OnKnowledgeClick(object? sender, RoutedEventArgs e)
    {
        _selectedLibraryResult = null;
        _librarySearchQuery = null;
        _knowledgeReturnToLibraryAvailable = false;
        _activeKnowledgeSourceId = null;
        BackToLibraryFromKnowledgeButton.IsEnabled = false;
        SetSection("knowledge", "知识库");
    }

    private void OnLearningNavigationClick(object? sender, RoutedEventArgs e) => SetSection("learning", "学习");

    private void OnLearningOpenLibraryClick(object? sender, RoutedEventArgs e) => OnLibraryClick(sender, e);

    private void OnLearningOpenJobsClick(object? sender, RoutedEventArgs e) => OnJobsClick(sender, e);

    private void OnLearningQueueSelectionChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (_hydratingLearningQueue || e.AddedItems.Count != 1 || e.AddedItems[0] is not LearningQueueRow selected)
            return;
        if (string.Equals(_selectedLearningItemKey, selected.ItemKey, StringComparison.Ordinal))
            return;
        _selectedLearningItemKey = selected.ItemKey;
        OnLearningClick(this, new RoutedEventArgs());
    }

    private void OnEvidenceClick(object? sender, RoutedEventArgs e)
    {
        _activeEvidenceSourceId = null;
        SetSection("evidence", "证据中心");
    }

    private void OnOpenEvidenceSourceClick(object? sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_activeEvidenceSourceId) || _activeEvidenceSourceId == "—")
        {
            EvidenceAnchorDetailText.Text = "当前 Evidence anchor 未暴露 source_id，无法打开来源成员。";
            return;
        }

        _returnToLibraryAvailable = false;
        _knowledgeReturnToLibraryAvailable = false;
        _sourceReaderReturnToKnowledgeAvailable = false;
        _sourceReaderReturnKnowledgeId = null;
        BackToLibraryButton.IsEnabled = false;
        BackToLibraryFromKnowledgeButton.IsEnabled = false;
        SourceReaderIdBox.Text = _activeEvidenceSourceId;
        SetSection("source-reader", "导入阅读");
        OnReadSourceMembersClick(sender, e);
    }

    private void OnEvidenceOpenCaptureClick(object? sender, RoutedEventArgs e) => OnCaptureClick(sender, e);

    private void OnEvidenceOpenJobsClick(object? sender, RoutedEventArgs e) => OnJobsClick(sender, e);

    private void OnMemoryMapLoadClick(object? sender, RoutedEventArgs e) => _ = RefreshMemoryMapAsync();

    private void OnOpenMemoryMapSourceClick(object? sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_activeMemoryMapSourceId) || _activeMemoryMapSourceId == "—")
        {
            MemoryMapResultsText.Text = "当前 Knowledge lineage 未暴露 source_id，无法打开来源成员。";
            return;
        }

        _returnToLibraryAvailable = false;
        _knowledgeReturnToLibraryAvailable = false;
        _sourceReaderReturnToKnowledgeAvailable = false;
        _sourceReaderReturnKnowledgeId = null;
        BackToLibraryButton.IsEnabled = false;
        BackToLibraryFromKnowledgeButton.IsEnabled = false;
        SourceReaderIdBox.Text = _activeMemoryMapSourceId;
        SetSection("source-reader", "导入阅读");
        OnReadSourceMembersClick(sender, e);
    }

    private void OnUnavailableHomeClick(object? sender, RoutedEventArgs e) => OnHomeClick(sender, e);

    private void OnUnavailableSettingsClick(object? sender, RoutedEventArgs e) => OnSettingsClick(sender, e);

    private void OnOpenLearningKnowledgeClick(object? sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_activeKnowledgeId))
        {
            CoreStatusText.Text = "学习路径：当前没有可打开的 Knowledge 投影";
            return;
        }
        KnowledgeIdBox.Text = _activeKnowledgeId;
        SetSection("knowledge", "知识详情");
        OnReadKnowledgeClick(sender, e);
    }

    private void OnResearchClick(object? sender, RoutedEventArgs e) => SetSection("research", "研究");

    private void OnOriginalEditorClick(object? sender, RoutedEventArgs e) => SetSection("original-editor", "原件编辑");

    private void OnMemoryMapClick(object? sender, RoutedEventArgs e) => SetSection("memory-map", "记忆地图");

    private void OnMachineGrowthClick(object? sender, RoutedEventArgs e) => SetSection("machine-growth", "机器知识");

    private void OnJobsClick(object? sender, RoutedEventArgs e) => SetSection("jobs", "任务");

    private void OnPluginsClick(object? sender, RoutedEventArgs e) => SetSection("plugins", "插件");

    private void OnModelsClick(object? sender, RoutedEventArgs e) => SetSection("models", "模型");

    private void OnSettingsClick(object? sender, RoutedEventArgs e) => SetSection("settings", "设置");

    private void OnSettingsRefreshClick(object? sender, RoutedEventArgs e) => _ = RefreshSettingsAsync();

    private void OnRecoveryClick(object? sender, RoutedEventArgs e) => SetSection("recovery", "恢复");

    private Task LoadLearningIfNeededAsync()
    {
        if (!LearningSurface.IsVisible)
            return Task.CompletedTask;
        OnLearningClick(this, new RoutedEventArgs());
        return Task.CompletedTask;
    }

    private Task ReadRecoveryStatusAsync()
    {
        if (!RecoverySurface.IsVisible)
            return Task.CompletedTask;
        OnReadRecoveryStatusClick(this, new RoutedEventArgs());
        return Task.CompletedTask;
    }

    private void SetCommandPaletteVisibility(bool visible)
    {
        if (visible)
        {
            _commandPaletteReturnFocus = FocusManager.GetFocusedElement();
            RevealSurface(CommandPaletteOverlay);
            CommandPaletteBox.Text = string.Empty;
            RefreshCommandPaletteResults(string.Empty);
            CommandPaletteBox.Focus();
            return;
        }

        CommandPaletteOverlay.Opacity = 1;
        CommandPaletteOverlay.IsVisible = false;
        var returnFocus = _commandPaletteReturnFocus;
        _commandPaletteReturnFocus = null;
        returnFocus?.Focus();
    }

    private void OnWindowKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.K && (e.KeyModifiers & KeyModifiers.Control) != 0)
        {
            SetCommandPaletteVisibility(!CommandPaletteOverlay.IsVisible);
            e.Handled = true;
            return;
        }

        if (e.Key == Key.Escape && CommandPaletteOverlay.IsVisible)
        {
            SetCommandPaletteVisibility(false);
            e.Handled = true;
            return;
        }

        if (e.Key == Key.Escape && _inspectorDrawerOpen && InspectorPanel.IsVisible)
        {
            OnToggleInspectorDrawerClick(this, new RoutedEventArgs());
            InspectorDrawerButton.Focus();
            e.Handled = true;
            return;
        }

        if (e.Key == Key.Escape && _activityDockExpanded)
        {
            SetActivityDockExpanded(false, restoreFocus: true);
            e.Handled = true;
        }
    }

    private void OnCommandPaletteKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape)
        {
            SetCommandPaletteVisibility(false);
            e.Handled = true;
            return;
        }

        if (e.Key == Key.Tab)
        {
            var reverse = (e.KeyModifiers & KeyModifiers.Shift) == KeyModifiers.Shift;
            if (reverse)
            {
                if (ReferenceEquals(sender, CommandPaletteResultsList))
                    CommandPaletteBox.Focus();
                else
                    CommandPaletteResultsList.Focus();
            }
            else
            {
                if (ReferenceEquals(sender, CommandPaletteBox))
                    CommandPaletteResultsList.Focus();
                else
                    CommandPaletteBox.Focus();
            }
            e.Handled = true;
            return;
        }

        if (e.Key is Key.Up or Key.Down)
        {
            var count = CommandPaletteResultsList.ItemCount;
            if (count > 0)
            {
                var current = CommandPaletteResultsList.SelectedIndex < 0
                    ? 0
                    : CommandPaletteResultsList.SelectedIndex;
                var next = e.Key == Key.Down
                    ? Math.Min(current + 1, count - 1)
                    : Math.Max(current - 1, 0);
                CommandPaletteResultsList.SelectedIndex = next;
                SetCommandPaletteStatus($"已选择“{CommandPaletteResultsList.SelectedItem}”；按 Enter 执行。");
            }
            e.Handled = true;
            return;
        }

        if (e.Key == Key.Enter)
        {
            var selected = CommandPaletteResultsList.SelectedItem as string;
            ExecuteCommandPaletteCommand(string.IsNullOrWhiteSpace(selected) ? CommandPaletteBox.Text : selected);
            e.Handled = true;
        }
    }

    private void OnCommandPaletteTextChanged(object? sender, TextChangedEventArgs e)
        => RefreshCommandPaletteResults(CommandPaletteBox.Text);

    private void OnCommandPaletteSelectionChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (CommandPaletteResultsList.SelectedItem is string selected)
            SetCommandPaletteStatus($"已选择“{selected}”；按 Enter 执行。");
    }

    private void SetCommandPaletteStatus(string text)
    {
        CommandPaletteStatusText.Text = text;
        Avalonia.Automation.AutomationProperties.SetName(CommandPaletteStatusText, text);
    }

    private void OnCommandPaletteResultDoubleTapped(object? sender, TappedEventArgs e)
    {
        if (CommandPaletteResultsList.SelectedItem is not string selected)
            return;

        ExecuteCommandPaletteCommand(selected);
        e.Handled = true;
    }

    private void OnToolbarInputKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key != Key.Enter)
            return;

        if (ReferenceEquals(sender, LibrarySearchBox))
            OnSearchLibraryClick(sender, new RoutedEventArgs());
        else if (ReferenceEquals(sender, SourceReaderIdBox))
            OnReadSourceMembersClick(sender, new RoutedEventArgs());
        else if (ReferenceEquals(sender, KnowledgeIdBox))
            OnReadKnowledgeClick(sender, new RoutedEventArgs());
        else if (ReferenceEquals(sender, MachineTaskIdBox))
            OnReadMachineTaskClick(sender, new RoutedEventArgs());
        else if (ReferenceEquals(sender, JobLookupIdBox))
            OnReadJobReceiptClick(sender, new RoutedEventArgs());
        else if (ReferenceEquals(sender, MemoryMapKnowledgeIdBox))
            _ = RefreshMemoryMapAsync();
        else
            return;

        e.Handled = true;
    }

    private void RefreshCommandPaletteResults(string? rawQuery)
    {
        var query = rawQuery?.Trim() ?? string.Empty;
        var matches = CommandPaletteCommands
            .Where(command => query.Length == 0 || command.Contains(query, StringComparison.OrdinalIgnoreCase))
            .ToArray();
        CommandPaletteResultsList.ItemsSource = matches;
        CommandPaletteResultsList.SelectedIndex = matches.Length > 0 ? 0 : -1;
        SetCommandPaletteStatus(matches.Length == 0
            ? "未找到可执行页面；可用命令仅切换现有页面，不创建新状态。"
            : "选择命令后按 Enter 执行；命令只切换现有页面，不创建新状态。");
    }

    private void ExecuteCommandPaletteCommand(string? rawCommand)
    {
        var command = rawCommand?.Trim() ?? string.Empty;
        var route = CommandPaletteRoutes.FirstOrDefault(candidate => candidate.Matches(command));
        if (route is null)
        {
            SetCommandPaletteStatus($"未识别命令；可用：{string.Join("、", CommandPaletteRoutes.Select(candidate => candidate.Label))}。");
            return;
        }

        SetSection(route.Section, route.Heading);
        SetCommandPaletteVisibility(false);
    }

    private void ResetSourceReaderSelection()
    {
        ++_sourceTransformRequestVersion;
        SourceReaderMembersList.ItemsSource = Array.Empty<SourceMemberRow>();
        SourceReaderSelectedText.Text = "尚未选择来源成员。";
        SourceReaderMemberFieldText.Text = "未选择";
        SourceReaderOriginalNameFieldText.Text = "未选择";
        SourceReaderReadableFieldText.Text = "未选择";
        SourceReaderJobFieldText.Text = "未选择";
        SourceReaderShaFieldText.Text = "未选择";
        SourceReaderMemberBoundaryText.Text = "原文正文未暴露；字段来自 Core 来源成员投影。";
        SourceReaderTransformText.Text = "尚未读取转换输出；原文正文仍未暴露。";
        ReadSourceTransformButton.IsEnabled = false;
        CopySourceProvenanceButton.IsEnabled = false;
        CopySourceCitationButton.IsEnabled = false;
        SourceReaderChainSourceText.Text = "容器来源：未读取";
        SourceReaderChainMemberText.Text = "成员：未选择";
        SourceReaderChainJobText.Text = "处理任务：未选择";
        SourceReaderChainShaText.Text = "内容指纹：未选择";
        SourceReaderChainBoundaryText.Text = "仅为 Core 来源成员投影；不代表正文、理解或证据 anchor。";
        SourceReaderCoreNoteText.Text = "Core 语义边界：尚未读取。";
        JobLookupIdBox.Text = string.Empty;
        ViewSourceJobButton.IsEnabled = false;
        FindLibraryFromSourceButton.IsEnabled = false;
        InspectorObjectText.Text = "未选择来源成员";
        InspectorDetailsText.Text = "Source Reader 尚未读取有效成员。";
        InspectorSourceText.Text = "未暴露";
        InspectorVersionText.Text = "未暴露";
        InspectorStatusText.Text = "未暴露";
        InspectorBoundaryText.Text = "字段缺失不推断";
        InspectorLayerText.Text = "Core projection · 类型未暴露";
        InspectorChainSourceText.Text = "来源 → 未暴露";
        InspectorChainVersionText.Text = "版本 → 未暴露";
        InspectorChainProjectionText.Text = "当前投影 → 未暴露";
        InspectorProvenanceText.Text = "来源链未加载；字段缺失不推断。";
    }

    private void FinishSourceReaderRequest(long requestVersion)
    {
        if (requestVersion != _sourceReaderRequestVersion)
            return;
        SourceReaderLoadButton.IsEnabled = true;
        SourceReaderIdBox.IsEnabled = true;
    }

    private bool IsCurrentSourceReaderRequest(long requestVersion, string requestedSourceId)
    {
        if (requestVersion != _sourceReaderRequestVersion)
            return false;
        if (string.Equals(SourceReaderIdBox.Text?.Trim(), requestedSourceId, StringComparison.Ordinal))
            return true;
        ResetSourceReaderSelection();
        SourceReaderResultsText.Text = "输入已变化，请重新读取；旧响应未写入界面。";
        SetStatus(SourceReaderStatusText, "来源阅读：输入已变化，请重新读取。", "empty");
        FinishSourceReaderRequest(requestVersion);
        return false;
    }

    private async void OnReadSourceMembersClick(object? sender, RoutedEventArgs e)
    {
        var requestVersion = ++_sourceReaderRequestVersion;
        SourceReaderLoadButton.IsEnabled = false;
        SourceReaderIdBox.IsEnabled = false;
        SetStatus(SourceReaderStatusText, "来源阅读：正在读取 Core。", "loading");
        ResetSourceReaderSelection();
        var sourceId = SourceReaderIdBox.Text?.Trim() ?? string.Empty;
        SourceReaderChainSourceText.Text = string.IsNullOrWhiteSpace(sourceId)
            ? "容器来源：未读取"
            : $"容器来源：{sourceId}";
        if (string.IsNullOrWhiteSpace(sourceId))
        {
            SourceReaderResultsText.Text = "请输入 source_id 后再读取。";
            SetStatus(SourceReaderStatusText, "来源阅读：请输入 source_id。", "empty");
            SourceReaderMembersList.ItemsSource = Array.Empty<string>();
            FinishSourceReaderRequest(requestVersion);
            return;
        }
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            SourceReaderResultsText.Text = "核心未就绪，无法读取来源成员。";
            SourceReaderCoreNoteText.Text = "Core 语义边界：未读取。";
            SourceReaderMembersList.ItemsSource = Array.Empty<string>();
            SetStatus(SourceReaderStatusText, "来源阅读：Core 未就绪。", "error");
            FinishSourceReaderRequest(requestVersion);
            return;
        }
        try
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Get,
                $"/api/v1/sources/{Uri.EscapeDataString(sourceId)}/members");
            if (!IsCurrentSourceReaderRequest(requestVersion, sourceId))
                return;
            if (!response.IsSuccessStatusCode)
            {
                var responseBody = string.Empty;
                try
                {
                    responseBody = (await response.Content.ReadAsStringAsync()).Replace("\r", " ").Replace("\n", " ").Trim();
                }
                catch (Exception)
                {
                    responseBody = string.Empty;
                }
                if (!IsCurrentSourceReaderRequest(requestVersion, sourceId))
                    return;
                if ((int)response.StatusCode == 404 && responseBody.Length == 0)
                    responseBody = "source not found";
                if (responseBody.Length > 120)
                    responseBody = responseBody[..120] + "…";
                SourceReaderResultsText.Text = string.IsNullOrWhiteSpace(responseBody)
                    ? $"Core 未返回来源成员（HTTP {(int)response.StatusCode}）。"
                    : $"Core 未返回来源成员（HTTP {(int)response.StatusCode}：{responseBody}）。";
                SourceReaderCoreNoteText.Text = "Core 语义边界：错误响应未形成来源成员投影。";
                SourceReaderMembersList.ItemsSource = Array.Empty<string>();
                SetStatus(
                    SourceReaderStatusText,
                    IsPermissionStatus(response.StatusCode)
                        ? "来源阅读：Core 拒绝当前访问权限，请检查会话或权限范围。"
                        : "来源阅读：读取失败。",
                    IsPermissionStatus(response.StatusCode) ? "permission" : "error");
                FinishSourceReaderRequest(requestVersion);
                return;
            }
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (!IsCurrentSourceReaderRequest(requestVersion, sourceId))
                return;
            var root = document.RootElement;
            var lines = new List<string>
            {
                $"Container：{ReadDisplayValue(root, "container_source_id")}",
                $"成员数：{ReadDisplayValue(root, "member_count")}",
                $"可读：{ReadDisplayValue(root, "readable_count")}",
                $"仅托管：{ReadDisplayValue(root, "custody_only_count")}",
            };
            var returnedContainerId = ReadDisplayValue(root, "container_source_id");
            var declaredMemberCount = root.TryGetProperty("member_count", out var memberCountValue)
                && memberCountValue.TryGetInt32(out var parsedMemberCount)
                ? parsedMemberCount
                : -1;
            var memberRows = new List<SourceMemberRow>();
            if (root.TryGetProperty("members", out var members) && members.ValueKind == JsonValueKind.Array)
            {
                foreach (var member in members.EnumerateArray())
                {
                    var memberRow = new SourceMemberRow(
                        ReadDisplayValue(member, "source_id"),
                        ReadDisplayValue(member, "member"),
                        ReadDisplayValue(member, "original_name"),
                        ReadDisplayValue(member, "sha256"),
                        ReadDisplayValue(member, "readable"),
                        ReadDisplayValue(member, "job_id"));
                    memberRows.Add(memberRow);
                    lines.Add($"- {memberRow.DisplayText}");
                }
            }
            if (returnedContainerId != "—" && !string.Equals(returnedContainerId, sourceId, StringComparison.Ordinal))
                lines.Add("警告：来源容器标识与请求不一致；未据此推断来源内容。");
            if (declaredMemberCount >= 0 && declaredMemberCount != memberRows.Count)
                lines.Add("警告：成员计数与 Core 返回数组不一致；未据此推断完整性。");
            if (memberRows.Count == 0)
                lines.Add("Core 返回 0 个来源成员；未显示原文正文；未推断转换状态。");
            SourceReaderResultsText.Text = string.Join("\n", lines);
            var note = ReadDisplayValue(root, "note");
            SourceReaderCoreNoteText.Text = note == "—"
                ? "Core 说明：未暴露额外来源成员语义。"
                : $"Core 说明：{note}";
            SourceReaderMembersList.ItemsSource = memberRows;
            SetStatus(
                SourceReaderStatusText,
                memberRows.Count == 0
                    ? "来源阅读：Core 返回空成员。"
                    : $"来源阅读：已读取 {memberRows.Count} 个 Core 来源成员。",
                memberRows.Count == 0 ? "empty" : "success");
            FinishSourceReaderRequest(requestVersion);
            SetInspectorProjection(sourceId, $"来源成员 · 可读 {ReadDisplayValue(root, "readable_count")} · 托管 {ReadDisplayValue(root, "custody_only_count")}\n来自 Core 来源成员投影。");
        }
        catch (Exception)
        {
            SourceReaderResultsText.Text = "来源成员读取中断。";
            SourceReaderCoreNoteText.Text = "Core 语义边界：读取中断，未形成来源成员投影。";
            SourceReaderMembersList.ItemsSource = Array.Empty<string>();
            SetStatus(SourceReaderStatusText, "来源阅读：读取中断。", "error");
            FinishSourceReaderRequest(requestVersion);
        }
    }

    private void OnSourceMemberSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (e.AddedItems.Count != 1
            || e.AddedItems[0] is not SourceMemberRow selected)
            return;
        ++_sourceTransformRequestVersion;
        JobLookupIdBox.Text = selected.JobId == "—" ? string.Empty : selected.JobId;
        ViewSourceJobButton.IsEnabled = !string.IsNullOrWhiteSpace(selected.JobId) && selected.JobId != "—";
        FindLibraryFromSourceButton.IsEnabled = !string.IsNullOrWhiteSpace(selected.SourceId) && selected.SourceId != "—";
        SourceReaderSelectedText.Text = $"source_id：{selected.SourceId}\nmember：{selected.Member}\noriginal_name：{selected.OriginalName}\nreadable：{selected.Readable}\njob_id：{selected.JobId}\nsha256：{selected.Sha256}";
        SourceReaderMemberFieldText.Text = selected.Member;
        SourceReaderOriginalNameFieldText.Text = selected.OriginalName;
        SourceReaderReadableFieldText.Text = selected.Readable;
        SourceReaderJobFieldText.Text = selected.JobId;
        SourceReaderShaFieldText.Text = selected.Sha256;
        SourceReaderMemberBoundaryText.Text = "原文正文未暴露；字段来自 Core 来源成员投影。";
        SourceReaderTransformText.Text = "尚未读取转换输出；原文正文仍未暴露。";
        ReadSourceTransformButton.IsEnabled = string.Equals(selected.Readable, "true", StringComparison.OrdinalIgnoreCase)
            && !string.IsNullOrWhiteSpace(selected.JobId)
            && selected.JobId != "—";
        CopySourceProvenanceButton.IsEnabled = HasProvenanceValue(selected.SourceId)
            && HasProvenanceValue(selected.Member)
            && HasProvenanceValue(selected.Sha256);
        CopySourceCitationButton.IsEnabled = CopySourceProvenanceButton.IsEnabled;
        SourceReaderChainSourceText.Text = $"容器来源：{selected.SourceId}";
        SourceReaderChainMemberText.Text = $"成员：{selected.Member} · {selected.OriginalName}";
        SourceReaderChainJobText.Text = $"处理任务：{selected.JobId}";
        SourceReaderChainShaText.Text = $"内容指纹：{selected.Sha256}";
        SourceReaderChainBoundaryText.Text = "仅为 Core 来源成员投影；readable 不代表已理解，sha256 不是正文或 anchor。";
        SetInspectorProjection(
            "来源成员",
            $"source_id={selected.SourceId}\nmember={selected.Member}\noriginal_name={selected.OriginalName}\nreadable={selected.Readable}\njob_id={selected.JobId}\nsha256={selected.Sha256}\n来源成员字段来自 Core；未暴露的原文正文不推断。",
            selected.SourceId,
            status: $"readable={selected.Readable}",
            layer: "Core projection · Source member");
    }

    private async void OnReadSourceTransformClick(object? sender, RoutedEventArgs e)
    {
        if (SourceReaderMembersList.SelectedItem is not SourceMemberRow selected
            || !string.Equals(selected.Readable, "true", StringComparison.OrdinalIgnoreCase)
            || string.IsNullOrWhiteSpace(selected.JobId)
            || selected.JobId == "—")
        {
            SourceReaderTransformText.Text = "当前成员不可读取转换输出；原文正文仍未暴露。";
            SetStatus(SourceReaderStatusText, "来源阅读：当前成员没有可读取的 Core 转换输出。", "empty");
            return;
        }
        var requestVersion = ++_sourceTransformRequestVersion;
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            SourceReaderTransformText.Text = "Core 未就绪，未读取转换输出；原文正文仍未暴露。";
            SetStatus(SourceReaderStatusText, "来源阅读：Core 未就绪，未读取转换输出。", "error");
            return;
        }
        SetStatus(SourceReaderStatusText, "来源阅读：正在读取 Core 转换输出。", "loading");
        try
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Get,
                $"/api/v1/jobs/{Uri.EscapeDataString(selected.JobId)}/outputs/text");
            if (!IsCurrentSourceTransformRequest(requestVersion, selected))
                return;
            if (!response.IsSuccessStatusCode)
            {
                var permissionDenied = IsPermissionStatus(response.StatusCode);
                SourceReaderTransformText.Text = permissionDenied
                    ? "Core 拒绝读取转换输出；原文正文仍未暴露。"
                    : $"Core 未返回可验证转换输出（HTTP {(int)response.StatusCode}）；原文正文仍未暴露。";
                SetStatus(
                    SourceReaderStatusText,
                    permissionDenied
                        ? "来源阅读：Core 拒绝当前访问权限，请检查会话或权限范围。"
                        : "来源阅读：转换输出不可用。",
                    permissionDenied ? "permission" : "empty");
                return;
            }
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (!IsCurrentSourceTransformRequest(requestVersion, selected))
                return;
            var content = ReadDisplayValue(document.RootElement, "content");
            SourceReaderTransformText.Text = content == "—"
                ? "Core 返回的转换输出为空；原文正文仍未暴露。"
                : $"{content}\n\n边界：这是 Core transform 输出，不等于原文正文、理解或已接受 Knowledge。";
            SetStatus(SourceReaderStatusText, "来源阅读：已读取 Core transform 输出。", "success");
        }
        catch (Exception)
        {
            if (!IsCurrentSourceTransformRequest(requestVersion, selected))
                return;
            SourceReaderTransformText.Text = "转换输出读取中断；原文正文仍未暴露。";
            SetStatus(SourceReaderStatusText, "来源阅读：转换输出读取中断。", "error");
        }
    }

    private bool IsCurrentSourceTransformRequest(long requestVersion, SourceMemberRow selected) =>
        requestVersion == _sourceTransformRequestVersion
        && ReferenceEquals(SourceReaderMembersList.SelectedItem, selected);

    private static async Task<bool> TrySetClipboardTextAsync(IClipboard clipboard, string text)
    {
        try
        {
            await clipboard.SetTextAsync(text);
            return true;
        }
        catch (Exception)
        {
            return false;
        }
    }

    private async void OnCopySourceProvenanceClick(object? sender, RoutedEventArgs e)
    {
        if (SourceReaderMembersList.SelectedItem is not SourceMemberRow selected)
        {
            SetStatus(SourceReaderStatusText, "来源阅读：尚未选择可复制的成员。", "empty");
            return;
        }
        if (!HasProvenanceValue(selected.SourceId)
            || !HasProvenanceValue(selected.Member)
            || !HasProvenanceValue(selected.Sha256))
        {
            SetStatus(SourceReaderStatusText, "来源阅读：来源链字段不完整，未复制占位值。", "empty");
            return;
        }

        var clipboard = TopLevel.GetTopLevel(this)?.Clipboard;
        if (clipboard is null)
        {
            SetStatus(SourceReaderStatusText, "来源阅读：剪贴板不可用，未复制任何内容。", "error");
            return;
        }

        var provenance = string.Join("\n", new[]
        {
            $"source_id: {selected.SourceId}",
            $"member: {selected.Member}",
            $"original_name: {selected.OriginalName}",
            $"job_id: {selected.JobId}",
            $"sha256: {selected.Sha256}",
            "boundary: Core 来源成员投影；不包含原文正文，不代表已理解或 evidence anchor。",
        });
        if (!await TrySetClipboardTextAsync(clipboard, provenance))
        {
            SetStatus(SourceReaderStatusText, "来源阅读：剪贴板写入失败，请重试；未确认复制成功。", "error");
            return;
        }
        SetStatus(SourceReaderStatusText, "来源阅读：已复制来源链摘要；未复制原文正文。", "success");
        ShowToast("已复制来源链摘要");
    }

    private async void OnCopySourceCitationClick(object? sender, RoutedEventArgs e)
    {
        if (SourceReaderMembersList.SelectedItem is not SourceMemberRow selected
            || !HasProvenanceValue(selected.SourceId)
            || !HasProvenanceValue(selected.Member)
            || !HasProvenanceValue(selected.Sha256))
        {
            SetStatus(SourceReaderStatusText, "来源阅读：引用字段不完整，未复制占位值。", "empty");
            return;
        }

        var clipboard = TopLevel.GetTopLevel(this)?.Clipboard;
        if (clipboard is null)
        {
            SetStatus(SourceReaderStatusText, "来源阅读：剪贴板不可用，未复制任何内容。", "error");
            return;
        }

        var citation = string.Join("\n", new[]
        {
            $"标题: {(HasProvenanceValue(selected.OriginalName) ? selected.OriginalName : selected.Member)}",
            $"source_id: {selected.SourceId}",
            $"member: {selected.Member}",
            $"job_id: {selected.JobId}",
            $"sha256: {selected.Sha256}",
            "boundary: 引用元数据来自 Core 来源成员投影；不包含原文正文，不代表 Evidence anchor 或 Knowledge Truth。",
        });
        if (!await TrySetClipboardTextAsync(clipboard, citation))
        {
            SetStatus(SourceReaderStatusText, "来源阅读：剪贴板写入失败，请重试；未确认复制成功。", "error");
            return;
        }
        SetStatus(SourceReaderStatusText, "来源阅读：已复制引用元数据；未复制原文正文。", "success");
        ShowToast("已复制引用元数据");
    }

    private void OnFindLibraryFromSourceClick(object? sender, RoutedEventArgs e)
    {
        if (SourceReaderMembersList.SelectedItem is not SourceMemberRow selected
            || string.IsNullOrWhiteSpace(selected.SourceId)
            || selected.SourceId == "—")
        {
            SourceReaderResultsText.Text = "当前成员未暴露 source_id，无法在资料库查找。";
            return;
        }

        LibrarySearchBox.Text = selected.SourceId.Trim();
        SetSection("library", "资料库");
        OnSearchLibraryClick(sender, e);
    }

    private void OnViewSourceJobClick(object? sender, RoutedEventArgs e)
    {
        var jobId = JobLookupIdBox.Text?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(jobId))
        {
            SourceReaderResultsText.Text = "当前成员未暴露 job_id，无法读取任务回执。";
            return;
        }
        SetSection("jobs", "任务");
        OnReadJobReceiptClick(sender, e);
    }

    private async void OnReadRecoveryStatusClick(object? sender, RoutedEventArgs e)
    {
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            SetStatus(RecoveryResultsText, "error · 核心未就绪，无法读取恢复边界状态。", "error");
            return;
        }
        try
        {
            using var versionResponse = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/system/version");
            using var workspaceResponse = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/workspaces/info");
            if (!versionResponse.IsSuccessStatusCode || !workspaceResponse.IsSuccessStatusCode)
            {
                var failedResponse = !versionResponse.IsSuccessStatusCode ? versionResponse : workspaceResponse;
                SetStatus(
                    RecoveryResultsText,
                    IsPermissionStatus(failedResponse.StatusCode)
                        ? "permission · Core 拒绝读取恢复边界状态，请检查会话或权限范围。"
                        : $"error · Core 状态读取失败（HTTP {(int)failedResponse.StatusCode}）；未执行任何恢复动作。",
                    IsPermissionStatus(failedResponse.StatusCode) ? "permission" : "error");
                return;
            }
            using var version = JsonDocument.Parse(await versionResponse.Content.ReadAsStringAsync());
            using var workspace = JsonDocument.Parse(await workspaceResponse.Content.ReadAsStringAsync());
            var sources = ReadOptionalInt(workspace.RootElement, "sources");
            var anchors = ReadOptionalInt(workspace.RootElement, "anchors");
            var recoveryText = string.Join("\n", new[]
            {
                $"Runtime：{ReadDisplayValue(version.RootElement, "runtime")}",
                $"Contract：{ReadDisplayValue(version.RootElement, "contract")}",
                $"Schema：{ReadDisplayValue(version.RootElement, "schema_version")}",
                $"工作区来源：{FormatOptionalCount(sources)} · 锚点：{FormatOptionalCount(anchors)}",
                "恢复点：当前 Core 未暴露",
                "恢复动作：未执行",
            });
            SetStatus(RecoveryResultsText, $"info · 恢复边界已读取；未执行恢复动作。\n{recoveryText}", "info");
            SetInspectorProjection("Recovery boundary", "Core 状态已读取；恢复点未暴露，未执行恢复动作。");
        }
        catch (JsonException)
        {
            SetStatus(RecoveryResultsText, "error · Recovery 响应不是有效 JSON；未执行任何恢复动作。", "error");
        }
        catch (Exception)
        {
            SetStatus(RecoveryResultsText, "error · 恢复边界状态读取中断；未执行任何恢复动作。", "error");
        }
    }

    private async void OnReadKnowledgeClick(object? sender, RoutedEventArgs e)
    {
        var requestVersion = ++_knowledgeRequestVersion;
        SetStatus(KnowledgeStateText, "正在读取 Knowledge V3。", "loading");
        var knowledgeId = KnowledgeIdBox.Text?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(knowledgeId))
        {
            SetStatus(KnowledgeStateText, "请输入 knowledge_id 后再读取。", "empty");
            KnowledgeResultsText.Text = "请输入 knowledge_id 后再读取。";
        KnowledgeStatusText.Text = "未暴露";
        KnowledgeSourceText.Text = "未暴露";
            KnowledgeTrustText.Text = "未暴露";
            KnowledgeReviewText.Text = "未暴露";
            KnowledgeObjectTitleText.Text = "标题：未读取";
            KnowledgeObjectMetaText.Text = "knowledge_id：未暴露 · owner：未暴露";
            KnowledgeBodyText.Text = "正文未读取；缺失字段不推断。";
            KnowledgeContextSourceText.Text = "来源：未暴露";
        KnowledgeContextVersionText.Text = "Knowledge 版本：未暴露";
        KnowledgeContextProjectionText.Text = "当前投影：未读取";
        KnowledgeContextBoundaryText.Text = "字段缺失不推断；Knowledge 状态不等于学习掌握。";
        _activeKnowledgeSourceId = null;
            OpenKnowledgeSourceButton.IsEnabled = false;
            return;
        }
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            SetStatus(KnowledgeStateText, "核心未就绪，无法读取知识投影。", "error");
            KnowledgeResultsText.Text = "核心未就绪，无法读取知识投影。";
            KnowledgeStatusText.Text = "Core 未就绪";
            KnowledgeSourceText.Text = "未读取";
            KnowledgeTrustText.Text = "未读取";
            KnowledgeReviewText.Text = "未读取";
            KnowledgeObjectTitleText.Text = "标题：Core 未就绪";
            KnowledgeObjectMetaText.Text = "knowledge_id：未读取 · owner：未读取";
            KnowledgeBodyText.Text = "正文未读取；Core 未就绪。";
            KnowledgeContextSourceText.Text = "来源：Core 未就绪";
            KnowledgeContextVersionText.Text = "Knowledge 版本：未读取";
            KnowledgeContextProjectionText.Text = "当前投影：未读取";
            KnowledgeContextBoundaryText.Text = "Core 未就绪；不推断知识状态。";
            _activeKnowledgeSourceId = null;
            OpenKnowledgeSourceButton.IsEnabled = false;
            return;
        }
        try
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Get,
                $"/api/v1/knowledge-items/{Uri.EscapeDataString(knowledgeId)}/v3");
            if (requestVersion != _knowledgeRequestVersion)
                return;
            if (!response.IsSuccessStatusCode)
            {
                var permissionDenied = IsPermissionStatus(response.StatusCode);
                var notFound = response.StatusCode == System.Net.HttpStatusCode.NotFound;
                SetStatus(
                    KnowledgeStateText,
                    permissionDenied
                        ? "Knowledge V3：Core 拒绝当前访问权限，请检查会话或权限范围。"
                        : notFound
                            ? "Knowledge V3：Core 未找到该知识对象。"
                            : $"Knowledge V3 读取失败（HTTP {(int)response.StatusCode}）。",
                    permissionDenied ? "permission" : notFound ? "empty" : "error");
                KnowledgeResultsText.Text = permissionDenied
                    ? "Core 拒绝返回知识投影；未保留旧对象内容。"
                    : notFound
                        ? "Core 未找到知识投影；请确认 knowledge_id。"
                        : $"Core 未返回知识投影（HTTP {(int)response.StatusCode}）。";
                KnowledgeStatusText.Text = permissionDenied ? "权限不足" : notFound ? "未找到" : "读取失败";
                KnowledgeSourceText.Text = "未读取";
                KnowledgeTrustText.Text = "未读取";
                KnowledgeReviewText.Text = "未读取";
                KnowledgeObjectTitleText.Text = permissionDenied
                    ? "标题：权限不足"
                    : notFound ? "标题：未找到" : "标题：读取失败";
                KnowledgeObjectMetaText.Text = "knowledge_id：未读取 · owner：未读取";
                KnowledgeBodyText.Text = permissionDenied
                    ? "正文未读取；Core 拒绝返回 Knowledge V3。"
                    : notFound ? "正文未读取；Knowledge 对象不存在。" : "正文未读取；Knowledge V3 读取失败。";
                KnowledgeContextSourceText.Text = permissionDenied ? "来源：权限不足" : notFound ? "来源：未找到" : "来源：读取失败";
                KnowledgeContextVersionText.Text = "Knowledge 版本：未读取";
                KnowledgeContextProjectionText.Text = "当前投影：读取失败";
                KnowledgeContextBoundaryText.Text = "读取失败；字段缺失不推断。";
                _activeKnowledgeSourceId = null;
                OpenKnowledgeSourceButton.IsEnabled = false;
                UpdateInspectorActions();
                return;
            }
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (requestVersion != _knowledgeRequestVersion)
                return;
            var root = document.RootElement;
            KnowledgeStatusText.Text = ReadDisplayValue(root, "status");
            KnowledgeSourceText.Text = ReadDisplayValue(root, "source_id");
            KnowledgeTrustText.Text = $"支持：{ReadDisplayValue(root, "support_level")} · 置信：{ReadDisplayValue(root, "confidence")} · 风险：{ReadDisplayValue(root, "risk_level")}";
            KnowledgeReviewText.Text = ReadDisplayValue(root, "requires_human_review");
            var knowledgeIdentity = ReadDisplayValue(root, "knowledge_id");
            var hasKnowledgeIdentity = knowledgeIdentity != "—" && !string.IsNullOrWhiteSpace(knowledgeIdentity);
            SetStatus(KnowledgeStateText, hasKnowledgeIdentity ? "Knowledge V3 已读取。" : "Knowledge V3 已响应，但标识字段未暴露。", hasKnowledgeIdentity ? "success" : "empty");
            _activeKnowledgeSourceId = ReadDisplayValue(root, "source_id");
            OpenKnowledgeSourceButton.IsEnabled = !string.IsNullOrWhiteSpace(_activeKnowledgeSourceId)
                && _activeKnowledgeSourceId != "—";
            KnowledgeContextSourceText.Text = $"来源：{ReadDisplayValue(root, "source_id")}";
            KnowledgeContextVersionText.Text = $"Knowledge 版本：{ReadDisplayValue(root, "knowledge_version")}";
            KnowledgeContextProjectionText.Text = $"当前投影：{ReadDisplayValue(root, "knowledge_id")} · {ReadDisplayValue(root, "status")}";
            KnowledgeContextBoundaryText.Text = ReadDisplayValue(root, "requires_human_review") == "true"
                ? "Core 标记需要人工复核；不把该标记解释为已接受。"
                : "字段缺失不推断；Knowledge 状态不等于学习掌握。";
            KnowledgeObjectTitleText.Text = $"标题：{ReadDisplayValue(root, "title")}";
            KnowledgeObjectMetaText.Text = $"knowledge_id：{ReadDisplayValue(root, "knowledge_id")} · owner：{ReadDisplayValue(root, "owner")}";
            KnowledgeBodyText.Text = ReadDisplayValue(root, "body");
            KnowledgeResultsText.Text = string.Join("\n", new[]
            {
                $"Knowledge：{ReadDisplayValue(root, "knowledge_id")}",
                $"类型：{ReadDisplayValue(root, "title")}",
                $"状态：{ReadDisplayValue(root, "status")}",
                $"Owner：{ReadDisplayValue(root, "owner")}",
                $"来源：{ReadDisplayValue(root, "source_id")}",
                $"正文：{ReadDisplayValue(root, "body")}",
            });
            SetInspectorProjection(
                ReadDisplayValue(root, "knowledge_id"),
                $"{ReadDisplayValue(root, "title")} · {ReadDisplayValue(root, "status")}\n来源：{ReadDisplayValue(root, "source_id")}\n来自 Core Knowledge V3 投影。",
                ReadDisplayValue(root, "source_id"),
                ReadDisplayValue(root, "knowledge_version"),
                ReadDisplayValue(root, "status"),
                boundary: ReadDisplayValue(root, "requires_human_review") == "true"
                    ? "Core 标记需要人工复核；不把该标记解释为已接受。"
                    : "Knowledge V3 字段来自 Core；未暴露字段不推断。",
                layer: "Core projection · Knowledge V3");
            UpdateInspectorActions();
        }
        catch (JsonException)
        {
            if (requestVersion != _knowledgeRequestVersion)
                return;
            SetStatus(KnowledgeStateText, "Knowledge V3 响应不是有效 JSON。", "error");
            KnowledgeResultsText.Text = "知识投影解析失败。";
            KnowledgeStatusText.Text = "解析失败";
            KnowledgeSourceText.Text = "未读取";
            KnowledgeTrustText.Text = "未读取";
            KnowledgeReviewText.Text = "未读取";
            KnowledgeObjectTitleText.Text = "标题：解析失败";
            KnowledgeObjectMetaText.Text = "knowledge_id：未读取 · owner：未读取";
            KnowledgeBodyText.Text = "正文未读取；响应解析失败。";
            KnowledgeContextSourceText.Text = "来源：解析失败";
            KnowledgeContextVersionText.Text = "Knowledge 版本：未读取";
            KnowledgeContextProjectionText.Text = "当前投影：解析失败";
            KnowledgeContextBoundaryText.Text = "响应解析失败；字段缺失不推断。";
            _activeKnowledgeSourceId = null;
            OpenKnowledgeSourceButton.IsEnabled = false;
            UpdateInspectorActions();
        }
        catch (Exception)
        {
            if (requestVersion != _knowledgeRequestVersion)
                return;
            SetStatus(KnowledgeStateText, "Knowledge V3 读取中断。", "error");
            KnowledgeResultsText.Text = "知识投影读取中断。";
            KnowledgeStatusText.Text = "读取中断";
            KnowledgeSourceText.Text = "未读取";
            KnowledgeTrustText.Text = "未读取";
            KnowledgeReviewText.Text = "未读取";
            KnowledgeObjectTitleText.Text = "标题：读取中断";
            KnowledgeObjectMetaText.Text = "knowledge_id：未读取 · owner：未读取";
            KnowledgeBodyText.Text = "正文未读取；请求已中断。";
            KnowledgeContextSourceText.Text = "来源：读取中断";
            KnowledgeContextVersionText.Text = "Knowledge 版本：未读取";
            KnowledgeContextProjectionText.Text = "当前投影：读取中断";
            KnowledgeContextBoundaryText.Text = "读取中断；字段缺失不推断。";
            _activeKnowledgeSourceId = null;
            OpenKnowledgeSourceButton.IsEnabled = false;
            UpdateInspectorActions();
        }
    }

    private async void OnReadMachineTaskClick(object? sender, RoutedEventArgs e)
    {
        var requestVersion = ++_machineTaskRequestVersion;
        var taskId = MachineTaskIdBox.Text?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(taskId))
        {
            MachineTaskResultsText.Text = "请输入 task_id 后再读取。";
            return;
        }
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            MachineTaskResultsText.Text = "核心未就绪，无法读取机器任务收据。";
            return;
        }
        try
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Get,
                $"/api/v1/machine/tasks/{Uri.EscapeDataString(taskId)}");
            if (requestVersion != _machineTaskRequestVersion || !string.Equals(_activeSection, "machine-growth", StringComparison.Ordinal))
                return;
            if (!response.IsSuccessStatusCode)
            {
                MachineTaskResultsText.Text = $"Core 未返回机器任务收据（HTTP {(int)response.StatusCode}）。";
                return;
            }
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (requestVersion != _machineTaskRequestVersion || !string.Equals(_activeSection, "machine-growth", StringComparison.Ordinal))
                return;
            var root = document.RootElement;
            MachineTaskResultsText.Text = string.Join("\n", new[]
            {
                $"Task：{ReadDisplayValue(root, "task_id")}",
                $"Knowledge version：{ReadDisplayValue(root, "knowledge_version")}",
                $"模型：{ReadDisplayValue(root, "model_version")}",
                $"结果：{ReadDisplayValue(root, "outcome")}",
                $"失败：{ReadDisplayValue(root, "failure")}",
                $"Retest of：{ReadDisplayValue(root, "retest_of")}",
            });
            SetInspectorProjection(ReadDisplayValue(root, "task_id"), $"模型：{ReadDisplayValue(root, "model_version")} · 结果：{ReadDisplayValue(root, "outcome")}\n来自 Core 机器任务收据。");
        }
        catch (Exception)
        {
            if (requestVersion != _machineTaskRequestVersion || !string.Equals(_activeSection, "machine-growth", StringComparison.Ordinal))
                return;
            MachineTaskResultsText.Text = "机器任务收据读取中断。";
        }
    }

    private void OnEvidenceRefreshClick(object? sender, RoutedEventArgs e) => _ = RefreshEvidenceAsync();

    private void OnEvidenceAnchorSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (e.AddedItems.Count != 1 || e.AddedItems[0] is not EvidenceAnchorRow selected)
            return;
        EvidenceAnchorDetailText.Text = selected.DetailText;
        _activeEvidenceSourceId = selected.SourceId;
        SetInspectorProjection(
            selected.AnchorId,
            selected.DetailText,
            selected.RawSha256,
            selected.SourceRevision,
            status: "persisted",
            boundary: "Evidence anchor 仅定位来源证据；不等于 Knowledge 接受或学习掌握。",
            layer: "Core projection · Evidence anchor");
    }

    private async Task RefreshEvidenceAsync()
    {
        var requestVersion = ++_evidenceRequestVersion;
        EvidenceRefreshButton.IsEnabled = false;
        EvidenceAnchorDetailText.Text = "尚未选择 Evidence anchor。";
        EvidenceAnchorsList.ItemsSource = null;
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            EvidenceEmptyState.IsVisible = true;
            SetStatus(EvidenceStatusText, "Core 未就绪，未读取 Evidence。", "error");
            EvidenceBundlesText.Text = "Core 未就绪；bundle 仍未读取。";
            SetInspectorProjection("Evidence Center", "Core 未就绪，未读取 Evidence anchor。",
                status: "error",
                boundary: "不读取原文正文，不构造合成 anchor 或 bundle。",
                layer: "Core projection boundary · Evidence Center");
            EvidenceRefreshButton.IsEnabled = true;
            return;
        }
        SetStatus(EvidenceStatusText, "正在读取 Core Evidence anchor。", "loading");
        try
        {
            using var response = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/evidence/anchors");
            if (requestVersion != _evidenceRequestVersion || !string.Equals(_activeSection, "evidence", StringComparison.Ordinal))
                return;
            if (!response.IsSuccessStatusCode)
            {
                EvidenceEmptyState.IsVisible = true;
                var detail = string.Empty;
                try { detail = (await response.Content.ReadAsStringAsync()).Trim(); } catch (Exception) { }
                if (detail.Length > 120) detail = detail[..120] + "…";
                SetStatus(EvidenceStatusText,
                    IsPermissionStatus(response.StatusCode) ? "Evidence：Core 拒绝当前访问权限。" : "Evidence：读取失败。",
                    IsPermissionStatus(response.StatusCode) ? "permission" : "error");
                EvidenceBundlesText.Text = string.IsNullOrWhiteSpace(detail)
                    ? $"Core 未返回 Evidence anchor（HTTP {(int)response.StatusCode}）。"
                    : $"Core 未返回 Evidence anchor（HTTP {(int)response.StatusCode}：{detail}）。";
                SetInspectorProjection("Evidence Center", EvidenceBundlesText.Text,
                    status: IsPermissionStatus(response.StatusCode) ? "permission" : "error",
                    boundary: "Core 错误响应未形成 Evidence 投影；不构造合成数据。",
                    layer: "Core projection boundary · Evidence Center");
                return;
            }
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (requestVersion != _evidenceRequestVersion || !string.Equals(_activeSection, "evidence", StringComparison.Ordinal))
                return;
            var rows = new List<EvidenceAnchorRow>();
            if (document.RootElement.TryGetProperty("items", out var items) && items.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in items.EnumerateArray())
                {
                    var anchorId = ReadDisplayValue(item, "anchor_id");
                    if (string.IsNullOrWhiteSpace(anchorId) || anchorId == "未暴露") continue;
                    rows.Add(new EvidenceAnchorRow(
                        anchorId,
                        ReadDisplayValue(item, "source_id"),
                        ReadDisplayValue(item, "raw_sha256"),
                        ReadDisplayValue(item, "source_revision"),
                        ReadDisplayValue(item, "position")));
                }
            }
            EvidenceAnchorsList.ItemsSource = rows;
            EvidenceEmptyState.IsVisible = rows.Count == 0;
            EvidenceBundlesText.Text = "Core 当前未暴露 Evidence bundle 读模型；仅显示已持久化 anchor。";
            var status = rows.Count == 0 ? "Core 已响应，但当前没有 Evidence anchor。" : $"Core 已返回 {rows.Count} 个 Evidence anchor。";
            SetStatus(EvidenceStatusText, status, rows.Count == 0 ? "empty" : "success");
            SetInspectorProjection("Evidence Center", status,
                status: rows.Count == 0 ? "empty" : "persisted",
                boundary: "anchor 仅提供来源定位，不包含原文正文，也不等于 Knowledge 接受或学习掌握。",
                layer: "Core projection · Evidence anchor");
        }
        catch (Exception ex)
        {
            if (requestVersion != _evidenceRequestVersion || !string.Equals(_activeSection, "evidence", StringComparison.Ordinal))
                return;
            SetStatus(EvidenceStatusText, "Evidence：读取响应无法解析。", "error");
            EvidenceBundlesText.Text = $"Core Evidence 响应未形成列表：{ex.Message}";
            SetInspectorProjection("Evidence Center", "Evidence 响应无法解析。",
                status: "error",
                boundary: "解析失败不产生 Evidence 投影；不构造合成数据。",
                layer: "Core projection boundary · Evidence Center");
        }
        finally
        {
            if (requestVersion == _evidenceRequestVersion)
                EvidenceRefreshButton.IsEnabled = true;
        }
    }

    private static string FormatEvidenceBundles(JsonElement root)
    {
        if (!root.TryGetProperty("items", out var items) || items.ValueKind != JsonValueKind.Array)
            return "Core 未暴露 bundle items。";
        var lines = new List<string>();
        foreach (var item in items.EnumerateArray())
        {
            lines.Add($"bundle_id={ReadDisplayValue(item, "bundle_id")} · " +
                $"status={ReadDisplayValue(item, "status")} · " +
                $"version={ReadDisplayValue(item, "version")}");
        }
        return lines.Count == 0 ? "Core 已响应，但当前没有 Evidence bundle。" : string.Join("\n", lines);
    }

    private async Task RefreshMemoryMapAsync()
    {
        var requestVersion = ++_memoryMapRequestVersion;
        MemoryMapLoadButton.IsEnabled = false;
        var knowledgeId = MemoryMapKnowledgeIdBox.Text?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(knowledgeId))
        {
            MemoryMapResultsText.Text = "请输入 knowledge_id 后读取 Core Knowledge lineage。";
            SetStatus(MemoryMapStatusText, "记忆地图：请输入 knowledge_id。", "empty");
            MemoryMapLoadButton.IsEnabled = true;
            return;
        }
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            MemoryMapResultsText.Text = "Core 未就绪，无法读取 Knowledge lineage。";
            SetStatus(MemoryMapStatusText, "记忆地图：Core 未就绪。", "error");
            MemoryMapLoadButton.IsEnabled = true;
            return;
        }

        SetStatus(MemoryMapStatusText, "记忆地图：正在读取 Core Knowledge lineage。", "loading");
        try
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Get,
                $"/api/v1/knowledge-items/{Uri.EscapeDataString(knowledgeId)}/v3");
            if (requestVersion != _memoryMapRequestVersion || !string.Equals(_activeSection, "memory-map", StringComparison.Ordinal))
                return;
            if (!response.IsSuccessStatusCode)
            {
                var detail = string.Empty;
                try { detail = (await response.Content.ReadAsStringAsync()).Trim(); } catch (Exception) { }
                if (detail.Length > 120) detail = detail[..120] + "…";
                MemoryMapResultsText.Text = string.IsNullOrWhiteSpace(detail)
                    ? $"Core 未返回 Knowledge lineage（HTTP {(int)response.StatusCode}）。"
                    : $"Core 未返回 Knowledge lineage（HTTP {(int)response.StatusCode}：{detail}）。";
                SetStatus(MemoryMapStatusText,
                    IsPermissionStatus(response.StatusCode) ? "记忆地图：Core 拒绝当前访问权限。" : "记忆地图：Knowledge lineage 读取失败。",
                    IsPermissionStatus(response.StatusCode) ? "permission" : "error");
                return;
            }

            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (requestVersion != _memoryMapRequestVersion || !string.Equals(_activeSection, "memory-map", StringComparison.Ordinal))
                return;
            var root = document.RootElement;
            var supersedes = FormatRelationIds(root, "supersedes");
            var supersededBy = FormatRelationIds(root, "superseded_by");
            var sourceId = ReadDisplayValue(root, "source_id");
            _activeMemoryMapSourceId = sourceId;
            var status = ReadDisplayValue(root, "status");
            MemoryMapResultsText.Text = string.Join("\n", new[]
            {
                $"knowledge_id={ReadDisplayValue(root, "knowledge_id")}",
                $"title={ReadDisplayValue(root, "title")}",
                $"status={status}",
                $"source_id={sourceId}",
                $"supersedes={supersedes}",
                $"superseded_by={supersededBy}",
                "这是 Core Knowledge lineage 投影，不冒充 Memory Graph 节点、边或认知结论。",
            });
            SetStatus(MemoryMapStatusText, "记忆地图：已读取 Core Knowledge lineage。", "success");
            SetInspectorProjection(
                ReadDisplayValue(root, "knowledge_id"),
                $"Knowledge lineage · {status}\n来源：{sourceId}",
                sourceId,
                $"supersedes={supersedes}",
                status,
                "仅展示 Core 已持久化的版本关系；不冒充 Memory Graph 或学习掌握。",
                layer: "Core projection · Knowledge lineage");
        }
        catch (JsonException)
        {
            if (requestVersion != _memoryMapRequestVersion || !string.Equals(_activeSection, "memory-map", StringComparison.Ordinal))
                return;
            MemoryMapResultsText.Text = "Core Knowledge lineage 响应不是有效 JSON。";
            SetStatus(MemoryMapStatusText, "记忆地图：响应解析失败。", "error");
        }
        catch (Exception ex)
        {
            if (requestVersion != _memoryMapRequestVersion || !string.Equals(_activeSection, "memory-map", StringComparison.Ordinal))
                return;
            MemoryMapResultsText.Text = $"Core Knowledge lineage 读取中断：{ex.Message}";
            SetStatus(MemoryMapStatusText, "记忆地图：读取中断。", "error");
        }
        finally
        {
            if (requestVersion == _memoryMapRequestVersion)
                MemoryMapLoadButton.IsEnabled = true;
        }
    }

    private static string FormatRelationIds(JsonElement root, string propertyName)
    {
        if (!root.TryGetProperty(propertyName, out var values) || values.ValueKind != JsonValueKind.Array)
            return "未暴露";
        var ids = values.EnumerateArray()
            .Where(value => value.ValueKind == JsonValueKind.String)
            .Select(value => value.GetString())
            .Where(value => !string.IsNullOrWhiteSpace(value))
            .ToArray();
        return ids.Length == 0 ? "无" : string.Join(", ", ids);
    }

    private async Task RefreshSettingsAsync()
    {
        SettingsRefreshButton.IsEnabled = false;
        SetStatus(SettingsStateText, "正在读取 Core 版本与工作区状态。", "loading");
        SettingsCoreStatusText.Classes.Set("status-version", false);
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            SetStatus(SettingsStateText, "Core 未就绪，未读取状态。", "error");
            SettingsCoreStatusText.Text = "核心未就绪。";
            SettingsWorkspaceStatusText.Text = "工作区：Core 未连接，未读取。";
            SettingsRefreshButton.IsEnabled = true;
            return;
        }
        try
        {
            using var response = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/system/version");
            if (!response.IsSuccessStatusCode)
            {
                if ((int)response.StatusCode == 401)
                    SetStatus(SettingsStateText, $"Core 会话凭据无效或已过期（HTTP {(int)response.StatusCode}）。", "permission");
                else if ((int)response.StatusCode == 403)
                    SetStatus(SettingsStateText, $"Core 拒绝当前访问来源或权限范围（HTTP {(int)response.StatusCode}）。", "permission");
                else
                    SetStatus(SettingsStateText, $"Core 版本端点读取失败（HTTP {(int)response.StatusCode}）。", "error");
                SettingsCoreStatusText.Text = "Core 版本读取失败。";
                SettingsWorkspaceStatusText.Text = "工作区：因 Core 版本读取失败而未读取。";
                return;
            }
            string? runtime;
            string? contract;
            string? schema;
            try
            {
                using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
                runtime = document.RootElement.TryGetProperty("runtime", out var runtimeValue)
                    ? runtimeValue.GetString() : null;
                contract = document.RootElement.TryGetProperty("contract", out var contractValue)
                    ? contractValue.GetString() : null;
                schema = document.RootElement.TryGetProperty("schema_version", out var schemaValue)
                    ? schemaValue.ToString() : null;
            }
            catch (JsonException)
            {
                SetStatus(SettingsStateText, "Core 版本响应不是有效 JSON；未读取工作区。", "error");
                SettingsCoreStatusText.Text = "Core 版本响应解析失败。";
                SettingsWorkspaceStatusText.Text = "工作区：因版本响应无效而未读取。";
                return;
            }
            using var workspaceResponse = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/workspaces/info");
            SettingsCoreStatusText.Text = $"Runtime：{runtime ?? "未知"}\nContract：{contract ?? "未知"}\nSchema：{schema ?? "未知"}";
            var hasVersionFields = !string.IsNullOrWhiteSpace(runtime)
                || !string.IsNullOrWhiteSpace(contract)
                || !string.IsNullOrWhiteSpace(schema);
            SettingsCoreStatusText.Classes.Set("status-version", hasVersionFields);
            if (workspaceResponse.IsSuccessStatusCode)
            {
                try
                {
                    using var workspace = JsonDocument.Parse(await workspaceResponse.Content.ReadAsStringAsync());
                    var sources = ReadOptionalInt(workspace.RootElement, "sources");
                    var anchors = ReadOptionalInt(workspace.RootElement, "anchors");
                    SettingsWorkspaceStatusText.Text = $"工作区：Core 已返回真实状态 · 来源 {FormatOptionalCount(sources)} · 锚点 {FormatOptionalCount(anchors)}";
                }
                catch (JsonException)
                {
                    SetStatus(SettingsStateText, "Core 版本已读取；工作区响应不是有效 JSON，未推断为可用。", "error");
                    SettingsWorkspaceStatusText.Text = "工作区：响应解析失败；未推断为可用。";
                    return;
                }
            }
            else
            {
                if ((int)workspaceResponse.StatusCode == 401)
                    SetStatus(SettingsStateText, $"Core 工作区会话凭据无效或已过期（HTTP {(int)workspaceResponse.StatusCode}）。", "permission");
                else if ((int)workspaceResponse.StatusCode == 403)
                    SetStatus(SettingsStateText, $"Core 拒绝工作区访问来源或权限范围（HTTP {(int)workspaceResponse.StatusCode}）。", "permission");
                else
                    SetStatus(SettingsStateText, $"Core 工作区端点读取失败（HTTP {(int)workspaceResponse.StatusCode}）。", "error");
                SettingsWorkspaceStatusText.Text = "工作区：Core 未返回状态；未推断为可用。";
                return;
            }
            SetStatus(SettingsStateText, hasVersionFields ? "Core 状态已读取。" : "Core 已响应，但版本字段未暴露。", hasVersionFields ? "success" : "empty");
            SettingsCapabilityBoundaryText.Text = "插件、模型、Sidecar 未接入权威 readiness 投影。";
            SetInspectorProjection("Core runtime", $"Runtime：{runtime ?? "未知"} · Contract：{contract ?? "未知"}\nSchema：{schema ?? "未知"}\n来自 Core system/version 与 workspace/info 投影。");
        }
        catch (JsonException)
        {
            SetStatus(SettingsStateText, "Core 状态响应不是有效 JSON。", "error");
            SettingsCoreStatusText.Text = "Core 状态解析失败。";
            SettingsWorkspaceStatusText.Text = "工作区：未读取；响应解析失败。";
        }
        catch (Exception)
        {
            SetStatus(SettingsStateText, "Core 状态读取中断。", "error");
            SettingsCoreStatusText.Text = "Core 版本读取中断。";
            SettingsWorkspaceStatusText.Text = "工作区：读取中断；未推断为可用。";
        }
        finally
        {
            SettingsRefreshButton.IsEnabled = true;
        }
    }

    private static string ReadDisplayValue(JsonElement root, string name)
    {
        if (!root.TryGetProperty(name, out var value) || value.ValueKind == JsonValueKind.Null)
            return "—";
        return value.ValueKind == JsonValueKind.String ? value.GetString() ?? "—" : value.ToString();
    }

    private async void OnRefreshJobsClick(object? sender, RoutedEventArgs e) => await RefreshJobsAsync();

    private void OnToggleActivityDockClick(object? sender, RoutedEventArgs e)
    {
        SetActivityDockExpanded(!_activityDockExpanded);
    }

    private void SetActivityDockExpanded(bool expanded, bool restoreFocus = false)
    {
        _activityDockExpanded = expanded;
        if (_activityDockExpanded)
        {
            RevealSurface(ActivityDockDetailsText);
            RevealSurface(ActivityDockReceiptList);
        }
        else
        {
            ActivityDockDetailsText.Opacity = 1;
            ActivityDockReceiptList.Opacity = 1;
            ActivityDockDetailsText.IsVisible = false;
            ActivityDockReceiptList.IsVisible = false;
        }
        ActivityDockText.TextTrimming = _activityDockExpanded
            ? Avalonia.Media.TextTrimming.None
            : Avalonia.Media.TextTrimming.CharacterEllipsis;
        var label = _activityDockExpanded ? "收起活动回执详情" : "展开活动回执详情";
        ActivityDockToggleButton.Content = _activityDockExpanded ? "收起详情" : "展开详情";
        Avalonia.Automation.AutomationProperties.SetName(ActivityDockToggleButton, label);
        if (restoreFocus)
            ActivityDockToggleButton.Focus();
    }

    private void OnActivityDockReceiptSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (e.AddedItems.Count != 1 || e.AddedItems[0] is not JobReceiptRow selected)
            return;
        SetInspectorProjection(
            "Core 任务回执",
            $"{selected.Detail}\n来自当前会话 Core job/quality projection；不代表持久历史。",
            status: selected.SemanticState,
            layer: "Core projection · Job/Quality receipt");
    }

    private async void OnReadJobReceiptClick(object? sender, RoutedEventArgs e)
    {
        var requestVersion = ++_jobLookupRequestVersion;
        var jobId = JobLookupIdBox.Text?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(jobId))
        {
            SetStatus(JobLookupResultsText, "empty · 请输入 job_id 后再读取任务回执。", "empty");
            return;
        }
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            SetStatus(JobLookupResultsText, "error · Core 未就绪，无法读取指定任务回执。", "error");
            return;
        }
        SetStatus(JobLookupResultsText, "loading · 正在读取 Core 任务回执。", "loading");
        try
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Get,
                $"/api/v1/jobs/{Uri.EscapeDataString(jobId)}");
            if (requestVersion != _jobLookupRequestVersion || !string.Equals(_activeSection, "jobs", StringComparison.Ordinal))
                return;
            if (!response.IsSuccessStatusCode)
            {
                var permissionDenied = IsPermissionStatus(response.StatusCode);
                SetStatus(
                    JobLookupResultsText,
                    permissionDenied
                        ? "permission · Core 拒绝读取任务回执，请检查会话或权限范围。"
                        : response.StatusCode == System.Net.HttpStatusCode.NotFound
                            ? "empty · Core 未找到该任务回执。"
                            : $"error · Core 未返回任务回执（HTTP {(int)response.StatusCode}）；不代表任务成功。",
                    permissionDenied ? "permission" : response.StatusCode == System.Net.HttpStatusCode.NotFound ? "empty" : "error");
                return;
            }
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (requestVersion != _jobLookupRequestVersion || !string.Equals(_activeSection, "jobs", StringComparison.Ordinal))
                return;
            var lines = new List<string>
            {
                $"job_id：{ReadDisplayValue(document.RootElement, "job_id")}",
                $"状态：{ReadDisplayValue(document.RootElement, "state")}",
                $"attempt：{ReadDisplayValue(document.RootElement, "attempt")}",
                $"错误：{ReadDisplayValue(document.RootElement, "error")}",
                "以上为 Core 任务回执；job_id 存在不代表任务成功。",
            };
            var state = ReadDisplayValue(document.RootElement, "state");
            var semanticState = JobStateSemantic(state);
            SetStatus(JobLookupResultsText, string.Join("\n", lines), semanticState);
            SetInspectorProjection("指定任务回执", string.Join("\n", lines), status: semanticState, layer: "Core projection · Job receipt");
        }
        catch (Exception)
        {
            if (requestVersion != _jobLookupRequestVersion || !string.Equals(_activeSection, "jobs", StringComparison.Ordinal))
                return;
            SetStatus(JobLookupResultsText, "error · 任务回执读取中断；不代表任务成功。", "error");
        }
    }

    private async Task RefreshJobsAsync()
    {
        if (_sessionJobIds.Count == 0)
        {
            JobsResultsText.Text = "本次会话尚无可显示任务。";
            SetActivityDockSummary("本次会话暂无导入任务。");
            SetActivityDockDetails("当前会话没有可展开的 Core 回执。");
            JobsResultsList.ItemsSource = Array.Empty<JobReceiptRow>();
            ActivityDockReceiptList.ItemsSource = Array.Empty<JobReceiptRow>();
            SetStatus(ActivityDockStatusText, "empty · 本次会话暂无 Core 回执。", "empty");
            return;
        }
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            JobsResultsText.Text = "核心未就绪，无法读取本次导入状态。";
            SetActivityDockSummary("Core 未就绪，无法读取本次会话回执。");
            SetActivityDockDetails("Core 未就绪；没有可展开的回执详情。");
            JobsResultsList.ItemsSource = Array.Empty<JobReceiptRow>();
            ActivityDockReceiptList.ItemsSource = Array.Empty<JobReceiptRow>();
            SetStatus(ActivityDockStatusText, "error · Core 未就绪，无法读取本次会话回执。", "error");
            return;
        }
        SetStatus(ActivityDockStatusText, "loading · 正在读取本次会话 Core 回执。", "loading");
        var lines = new List<string>();
        var receipts = new List<JobReceiptRow>();
        var hasFailure = false;
        var hasPermissionFailure = false;
        var hasUnknown = false;
        var hasLoading = false;
        foreach (var jobId in _sessionJobIds)
        {
            try
            {
                using var statusResponse = await _supervisor.SendAsync(
                    HttpMethod.Get,
                    $"/api/v1/jobs/{Uri.EscapeDataString(jobId)}");
                if (!statusResponse.IsSuccessStatusCode)
                {
                    hasFailure = true;
                    hasPermissionFailure |= IsPermissionStatus(statusResponse.StatusCode);
                    var failureDetail = IsPermissionStatus(statusResponse.StatusCode)
                        ? $"{jobId}\n权限不足；Core 拒绝读取任务回执。"
                        : $"{jobId}\n状态读取失败（HTTP {(int)statusResponse.StatusCode}）。";
                    receipts.Add(new JobReceiptRow(jobId, IsPermissionStatus(statusResponse.StatusCode) ? "permission" : "error", failureDetail, IsPermissionStatus(statusResponse.StatusCode) ? "permission" : "error"));
                    continue;
                }
                using var status = JsonDocument.Parse(await statusResponse.Content.ReadAsStringAsync());
                var state = ReadDisplayValue(status.RootElement, "state");
                var semanticState = JobStateSemantic(state);
                hasUnknown |= semanticState == "unknown";
                hasLoading |= semanticState == "loading";
                var attempt = ReadDisplayValue(status.RootElement, "attempt");
                var error = ReadDisplayValue(status.RootElement, "error");
                var detail = $"{jobId}\n状态：{state} · attempt：{attempt}";
                if (error != "—") detail += $"\n错误：{error}";
                using var qualityResponse = await _supervisor.SendAsync(
                    HttpMethod.Get,
                    $"/api/v1/jobs/{Uri.EscapeDataString(jobId)}/quality");
                if (qualityResponse.IsSuccessStatusCode)
                {
                    using var quality = JsonDocument.Parse(await qualityResponse.Content.ReadAsStringAsync());
                    if (quality.RootElement.TryGetProperty("coverage", out var coverage)
                        && coverage.ValueKind != JsonValueKind.Null)
                    {
                        detail += $"\n质量回执：引擎 {ReadDisplayValue(quality.RootElement, "engine")} · 覆盖：{ReadDisplayValue(quality.RootElement, "covered")}/{ReadDisplayValue(quality.RootElement, "total")}";
                        detail += $" · loss：{ReadDisplayValue(quality.RootElement, "loss_count")} · regions：{ReadDisplayValue(quality.RootElement, "region_count")}";
                    }
                    else
                    {
                        detail += "\n质量回执：未生成；计数缺失不解释为已验证的零值。";
                    }
                }
                receipts.Add(new JobReceiptRow(jobId, state, detail, semanticState));
            }
            catch (Exception)
            {
                hasFailure = true;
                receipts.Add(new JobReceiptRow(jobId, "error", $"{jobId}\n状态读取中断", "error"));
            }
        }
        lines.AddRange(receipts.Select(receipt => receipt.Detail));
        JobsResultsText.Text = string.Join("\n\n", lines);
        JobsResultsList.ItemsSource = receipts;
        ActivityDockReceiptList.ItemsSource = receipts;
        SetActivityDockSummary($"本次会话 {lines.Count} 个任务 · 已读取 Core 状态与质量回执");
        SetActivityDockDetails(string.Join("\n\n", lines) + "\n\n以上为当前会话 Core 回执，不代表持久历史。");
        SetStatus(
            ActivityDockStatusText,
            hasPermissionFailure
                ? "permission · Core 拒绝部分任务回执；请检查会话或权限范围。"
                : hasFailure
                    ? "error · 部分任务回执读取失败；可刷新重试。"
                    : hasUnknown
                        ? "unknown · Core 返回了未识别任务状态；未推断为成功。"
                        : hasLoading
                            ? "loading · 部分任务仍在 Core 中处理。"
                            : "success · 当前会话 Core 回执已读取。",
            hasPermissionFailure ? "permission" : hasFailure ? "error" : hasUnknown ? "unknown" : hasLoading ? "loading" : "success");
        SetInspectorProjection("本次会话任务", $"任务数：{lines.Count}\n状态与质量回执来自 Core；不代表持久历史。");
    }

    private void OnJobReceiptSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (e.AddedItems.Count != 1 || e.AddedItems[0] is not JobReceiptRow selected)
            return;
        SetInspectorProjection(
            "Core 任务回执",
            $"{selected.Detail}\n来自当前会话 Core job/quality projection；不代表持久历史。",
            status: selected.SemanticState,
            layer: "Core projection · Job/Quality receipt");
    }

    private void OnMainFrameSizeChanged(object? sender, SizeChangedEventArgs e)
    {
        var inspectorBreakpoint = GetAaosBreakpoint("AaosInspectorBreakpoint", 1440);
        var narrowActionsBreakpoint = GetAaosBreakpoint("AaosNarrowActionsBreakpoint", 1280);
        var tabletBreakpoint = GetAaosBreakpoint("AaosTabletBreakpoint", 1024);
        var mobileBreakpoint = GetAaosBreakpoint("AaosMobileBreakpoint", 840);
        var sourceReaderStackBreakpoint = GetAaosBreakpoint("AaosSourceReaderStackBreakpoint", 1200);
        var hideInspector = e.NewSize.Width < inspectorBreakpoint;
        var hideContext = e.NewSize.Width < tabletBreakpoint;
        var compact = e.NewSize.Width <= tabletBreakpoint;
        var mobile = e.NewSize.Width < mobileBreakpoint;
        var narrowActions = e.NewSize.Width <= narrowActionsBreakpoint;
        InspectorDrawerButton.IsVisible = hideInspector;
        if (!hideInspector)
        {
            _inspectorDrawerOpen = false;
            InspectorDrawerButton.Content = "打开证据检查器";
            Avalonia.Automation.AutomationProperties.SetName(InspectorDrawerButton, "打开证据检查器");
            InspectorPanel.IsVisible = true;
            InspectorPanel.Width = double.NaN;
            InspectorPanel.HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Stretch;
            InspectorPanel.ZIndex = 0;
            Grid.SetColumn(InspectorPanel, 3);
            Grid.SetColumnSpan(InspectorPanel, 1);
        }
        else
        {
            InspectorPanel.IsVisible = _inspectorDrawerOpen;
            InspectorPanel.Width = 320;
            InspectorPanel.HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Right;
            InspectorPanel.ZIndex = 5;
            Grid.SetColumn(InspectorPanel, mobile ? 0 : 2);
            Grid.SetColumnSpan(InspectorPanel, mobile ? 4 : 1);
        }
        ContextSidebar.IsVisible = !hideContext;
        PrimaryRail.IsVisible = !mobile;
        MobileRail.IsVisible = mobile;
        Grid.SetColumn(WorkspaceScrollViewer, mobile ? 0 : 2);
        Grid.SetColumnSpan(WorkspaceScrollViewer, mobile ? 4 : 1);
        MainFrameGrid.ColumnDefinitions[0].Width = mobile ? new GridLength(0) : new GridLength(256);
        MainFrameGrid.ColumnDefinitions[3].Width = hideInspector ? new GridLength(0) : new GridLength(300);
        MainFrameGrid.ColumnDefinitions[1].Width = hideContext ? new GridLength(0) : new GridLength(220);
        WorkspaceScrollViewer.Padding = mobile
            ? new Avalonia.Thickness(16, 16)
            : new Avalonia.Thickness(32, 28);
        Grid.SetColumn(ActivityDock, compact ? 0 : 1);
        Grid.SetColumnSpan(ActivityDock, compact ? 4 : 3);
        ActivityDockGrid.RowDefinitions = compact
            ? new RowDefinitions("Auto,Auto")
            : new RowDefinitions("Auto");
        Grid.SetRow(ActivityDockActions, compact ? 1 : 0);
        Grid.SetColumn(ActivityDockActions, compact ? 0 : 1);
        CaptureContextActions.Orientation = narrowActions
            ? Avalonia.Layout.Orientation.Vertical
            : Avalonia.Layout.Orientation.Horizontal;
        LearningCaptureActions.Orientation = narrowActions
            ? Avalonia.Layout.Orientation.Vertical
            : Avalonia.Layout.Orientation.Horizontal;
        SourceReaderContextActions.Orientation = narrowActions
            ? Avalonia.Layout.Orientation.Vertical
            : Avalonia.Layout.Orientation.Horizontal;
        EvidenceEmptyStateContent.Orientation = compact
            ? Avalonia.Layout.Orientation.Vertical
            : Avalonia.Layout.Orientation.Horizontal;
        EvidenceEmptyStateImage.Width = compact ? 112 : 150;
        EvidenceEmptyStateImage.HorizontalAlignment = compact
            ? Avalonia.Layout.HorizontalAlignment.Center
            : Avalonia.Layout.HorizontalAlignment.Left;
        var inspectorActionsNarrow = narrowActions || InspectorPanel.IsVisible;
        InspectorActionPanel.Orientation = inspectorActionsNarrow
            ? Avalonia.Layout.Orientation.Vertical
            : Avalonia.Layout.Orientation.Horizontal;
        SetResponsiveToolbar(LibrarySearchGrid, LibrarySearchButton, narrowActions);
        LibraryWorkspaceGrid.ColumnDefinitions = compact
            ? new ColumnDefinitions("1*")
            : new ColumnDefinitions("1.1*,0.9*");
        LibraryWorkspaceGrid.RowDefinitions = compact
            ? new RowDefinitions("Auto,Auto")
            : new RowDefinitions("Auto");
        Grid.SetRow(LibrarySelectedDetailBorder, compact ? 1 : 0);
        Grid.SetColumn(LibrarySelectedDetailBorder, compact ? 0 : 1);
        SetResponsiveToolbar(SourceReaderLoadGrid, SourceReaderLoadButton, narrowActions);
        SetResponsiveToolbar(KnowledgeLoadGrid, KnowledgeLoadButton, narrowActions);
        SetResponsiveToolbar(MachineTaskGrid, MachineTaskLoadButton, narrowActions);
        SetResponsiveToolbar(JobLookupGrid, JobLookupButton, narrowActions);
        SetResponsiveToolbar(EvidenceToolbar, EvidenceRefreshButton, narrowActions);
        SetResponsiveToolbar(MemoryMapToolbar, MemoryMapLoadButton, narrowActions);
        HomeFocusGrid.ColumnDefinitions = compact
            ? new ColumnDefinitions("1*")
            : new ColumnDefinitions("*,*");
        HomeFocusGrid.RowDefinitions = compact
            ? new RowDefinitions("Auto,Auto")
            : new RowDefinitions("Auto");
        Grid.SetColumn(HomeFocusActionCard, compact ? 0 : 1);
        Grid.SetRow(HomeFocusActionCard, compact ? 1 : 0);
        HomeHeroGrid.ColumnDefinitions = compact
            ? new ColumnDefinitions("1*")
            : new ColumnDefinitions("*,220");
        HomeHeroGrid.RowDefinitions = compact
            ? new RowDefinitions("Auto,Auto")
            : new RowDefinitions("Auto");
        Grid.SetColumn(HomeHeroImage, compact ? 0 : 1);
        Grid.SetRow(HomeHeroImage, compact ? 1 : 0);
        HomeLifecycleGrid.ColumnDefinitions = compact
            ? new ColumnDefinitions("1*")
            : new ColumnDefinitions("*,*,*,*,*");
        HomeLifecycleGrid.RowDefinitions = compact
            ? new RowDefinitions("Auto,Auto,Auto,Auto,Auto")
            : new RowDefinitions("Auto");
        Grid.SetColumn(HomeLifecycleCaptureCard, 0);
        Grid.SetRow(HomeLifecycleCaptureCard, 0);
        Grid.SetColumn(HomeLifecycleSourceCard, compact ? 0 : 1);
        Grid.SetRow(HomeLifecycleSourceCard, compact ? 1 : 0);
        Grid.SetColumn(HomeLifecycleKnowledgeCard, compact ? 0 : 2);
        Grid.SetRow(HomeLifecycleKnowledgeCard, compact ? 2 : 0);
        Grid.SetColumn(HomeLifecycleLearningCard, compact ? 0 : 3);
        Grid.SetRow(HomeLifecycleLearningCard, compact ? 3 : 0);
        Grid.SetColumn(HomeLifecycleReviewCard, compact ? 0 : 4);
        Grid.SetRow(HomeLifecycleReviewCard, compact ? 4 : 0);
        var sourceReaderCompact = compact || e.NewSize.Width < sourceReaderStackBreakpoint;
        SourceReaderShellGrid.ColumnDefinitions = sourceReaderCompact
            ? new ColumnDefinitions("1*")
            : new ColumnDefinitions("220,*,300");
        SourceReaderShellGrid.RowDefinitions = sourceReaderCompact
            ? new RowDefinitions("Auto,Auto,Auto")
            : new RowDefinitions("Auto");
        Grid.SetColumn(SourceReaderOutlineBorder, 0);
        Grid.SetRow(SourceReaderOutlineBorder, 0);
        Grid.SetColumn(SourceReaderMainBorder, sourceReaderCompact ? 0 : 1);
        Grid.SetRow(SourceReaderMainBorder, sourceReaderCompact ? 1 : 0);
        Grid.SetColumn(SourceReaderChainBorder, sourceReaderCompact ? 0 : 2);
        Grid.SetRow(SourceReaderChainBorder, sourceReaderCompact ? 2 : 0);
        SetResponsiveToolbar(FirstRunReadinessGrid, FirstRunImportButton, narrowActions);
        SetResponsiveToolbar(HomeContinueReadingGrid, HomeContinueReadingButton, narrowActions);
        SetResponsiveToolbar(HomeDeepTutorGrid, HomeDeepTutorButton, narrowActions);
        SetResponsiveToolbar(HomeImportGrid, HomeImportButton, narrowActions);
        HomeKnowledgeActions.Orientation = narrowActions
            ? Avalonia.Layout.Orientation.Vertical
            : Avalonia.Layout.Orientation.Horizontal;
        HomeStatsSurface.ColumnDefinitions = compact
            ? new ColumnDefinitions("1*")
            : new ColumnDefinitions("*,*,*");
        HomeStatsSurface.RowDefinitions = compact
            ? new RowDefinitions("Auto,Auto,Auto")
            : new RowDefinitions("Auto");
        Grid.SetColumn(HomeStatsKnowledgeCard, compact ? 0 : 1);
        Grid.SetRow(HomeStatsKnowledgeCard, compact ? 1 : 0);
        Grid.SetColumn(HomeStatsLearningCard, compact ? 0 : 2);
        Grid.SetRow(HomeStatsLearningCard, compact ? 2 : 0);
        KnowledgeFactsGrid.ColumnDefinitions = compact
            ? new ColumnDefinitions("1*")
            : new ColumnDefinitions("*,*");
        KnowledgeFactsGrid.RowDefinitions = compact
            ? new RowDefinitions("Auto,Auto,Auto,Auto")
            : new RowDefinitions("Auto,Auto");
        Grid.SetColumn(KnowledgeStatusCard, 0);
        Grid.SetRow(KnowledgeStatusCard, 0);
        Grid.SetColumn(KnowledgeSourceCard, compact ? 0 : 1);
        Grid.SetRow(KnowledgeSourceCard, compact ? 1 : 0);
        Grid.SetColumn(KnowledgeTrustCard, 0);
        Grid.SetRow(KnowledgeTrustCard, compact ? 2 : 1);
        Grid.SetColumn(KnowledgeReviewCard, compact ? 0 : 1);
        Grid.SetRow(KnowledgeReviewCard, compact ? 3 : 1);
        ReviewActionsGrid.ColumnDefinitions = narrowActions
            ? new ColumnDefinitions("1*")
            : new ColumnDefinitions("*,*");
        ReviewActionsGrid.RowDefinitions = narrowActions
            ? new RowDefinitions("Auto,Auto,Auto,Auto")
            : new RowDefinitions("Auto,Auto");
        Grid.SetColumn(ReviewAgainButton, 0);
        Grid.SetRow(ReviewAgainButton, 0);
        Grid.SetColumn(ReviewHardButton, narrowActions ? 0 : 1);
        Grid.SetRow(ReviewHardButton, narrowActions ? 1 : 0);
        Grid.SetColumn(ReviewGoodButton, 0);
        Grid.SetRow(ReviewGoodButton, narrowActions ? 2 : 1);
        Grid.SetColumn(ReviewEasyButton, narrowActions ? 0 : 1);
        Grid.SetRow(ReviewEasyButton, narrowActions ? 3 : 1);
    }

    private double GetAaosBreakpoint(string key, double fallback)
    {
        if (this.TryFindResource(key, out var resource) && resource is double breakpoint)
            return breakpoint;
        return fallback;
    }

    private static void SetResponsiveToolbar(Grid grid, Control action, bool narrow)
    {
        grid.ColumnDefinitions = narrow
            ? new ColumnDefinitions("1*")
            : new ColumnDefinitions("*,Auto");
        grid.RowDefinitions = narrow
            ? new RowDefinitions("Auto,Auto")
            : new RowDefinitions("Auto");
        Grid.SetColumn(action, narrow ? 0 : 1);
        Grid.SetRow(action, narrow ? 1 : 0);
    }

    private async void OnSearchLibraryClick(object? sender, RoutedEventArgs e)
    {
        var requestVersion = ++_librarySearchRequestVersion;
        var query = LibrarySearchBox.Text?.Trim() ?? string.Empty;
        if (query.Length == 0)
        {
            LibraryResultsText.Text = "请输入关键词后再搜索。";
            SetStatus(LibrarySearchStatusText, "资料库搜索：请输入关键词。", "empty");
            LibraryResultsList.ItemsSource = Array.Empty<string>();
            LibrarySelectedDetailBorder.IsVisible = false;
            OpenLibrarySourceButton.IsEnabled = false;
            return;
        }
        _librarySearchQuery = query;
        LibrarySearchButton.IsEnabled = false;
        OpenLibrarySourceButton.IsEnabled = false;
        LibrarySelectedDetailBorder.IsVisible = false;
        SetStatus(LibrarySearchStatusText, "资料库搜索：正在读取 Core", "loading");
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            LibraryResultsText.Text = "核心未就绪，无法读取资料库。";
            SetStatus(LibrarySearchStatusText, "资料库搜索：核心未就绪。", "error");
            LibraryResultsList.ItemsSource = Array.Empty<string>();
            LibrarySelectedDetailBorder.IsVisible = false;
            LibrarySearchButton.IsEnabled = true;
            return;
        }
        try
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Get,
                $"/api/v1/search?q={Uri.EscapeDataString(query)}&active_only={(LibraryActiveOnlyBox.IsChecked == true).ToString().ToLowerInvariant()}");
            if (requestVersion != _librarySearchRequestVersion)
                return;
            if (!response.IsSuccessStatusCode)
            {
                var permissionDenied = IsPermissionStatus(response.StatusCode);
                LibraryResultsText.Text = permissionDenied
                    ? "Core 拒绝资料库搜索；请检查会话或权限范围。"
                    : "资料库搜索失败，请检查 Core 状态。";
                SetStatus(
                    LibrarySearchStatusText,
                    permissionDenied
                        ? "资料库搜索：Core 拒绝当前访问权限。"
                        : "资料库搜索：读取失败。",
                    permissionDenied ? "permission" : "error");
                LibraryResultsList.ItemsSource = Array.Empty<string>();
                LibrarySelectedDetailBorder.IsVisible = false;
                LibrarySearchButton.IsEnabled = true;
                return;
            }
            var responseBody = await response.Content.ReadAsStringAsync();
            if (requestVersion != _librarySearchRequestVersion)
                return;
            using var document = JsonDocument.Parse(responseBody);
            var rows = new List<LibraryResultRow>();
            var count = ReadInt(document.RootElement, "count");
            if (document.RootElement.TryGetProperty("items", out var items)
                && items.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in items.EnumerateArray())
                {
                    var id = item.TryGetProperty("knowledge_id", out var idValue)
                        ? idValue.GetString() : null;
                    var head = item.TryGetProperty("head", out var headValue)
                        ? headValue.GetString() : null;
                    if (!string.IsNullOrWhiteSpace(id))
                    {
                        rows.Add(new LibraryResultRow(
                            "knowledge",
                            id,
                            ReadDisplayValue(item, "source_id"),
                            ReadDisplayValue(item, "transform_id"),
                            ReadDisplayValue(item, "status"),
                            ReadDisplayValue(item, "active"),
                            ReadDisplayValue(item, "engine"),
                            head ?? "无标题"));
                    }
                }
            }
            var transformCount = ReadInt(document.RootElement, "transform_count");
            if (document.RootElement.TryGetProperty("transforms", out var transforms)
                && transforms.ValueKind == JsonValueKind.Array)
            {
                foreach (var transform in transforms.EnumerateArray())
                {
                    var sourceId = transform.TryGetProperty("source_id", out var sourceValue)
                        ? sourceValue.GetString() : null;
                    var head = transform.TryGetProperty("head", out var headValue)
                        ? headValue.GetString() : null;
                    if (!string.IsNullOrWhiteSpace(sourceId))
                    {
                        rows.Add(new LibraryResultRow(
                            "transform",
                            ReadDisplayValue(transform, "knowledge_id"),
                            sourceId,
                            ReadDisplayValue(transform, "transform_id"),
                            ReadDisplayValue(transform, "status"),
                            ReadDisplayValue(transform, "active"),
                            ReadDisplayValue(transform, "engine"),
                            head ?? "无标题"));
                    }
                }
            }
            var kindFilter = LibraryKindFilterBox.SelectedIndex switch
            {
                1 => "knowledge",
                2 => "transform",
                _ => "all",
            };
            var visibleRows = kindFilter == "all"
                ? rows
                : rows.Where(row => row.Kind == kindFilter).ToList();
            LibraryResultsText.Text = visibleRows.Count == 0
                ? $"未找到匹配结果（知识 {count}，提取结果 {transformCount}）。"
                : $"匹配结果：知识 {count}，提取结果 {transformCount}；当前显示 {visibleRows.Count} 条；选择一项查看来源摘要。";
            SetStatus(
                LibrarySearchStatusText,
                visibleRows.Count == 0
                    ? "资料库搜索：没有匹配结果。"
                    : $"资料库搜索：已读取 {visibleRows.Count} 条 Core 投影。",
                visibleRows.Count == 0 ? "empty" : "success");
            LibraryResultsList.ItemsSource = visibleRows;
            LibrarySelectedDetailBorder.IsVisible = false;
            SetInspectorProjection("资料库搜索", $"知识 {count} · 提取结果 {transformCount}\n当前筛选：{(kindFilter == "all" ? "全部类型" : kindFilter)} · active_only={LibraryActiveOnlyBox.IsChecked == true}\n查询：{query}\n来自 Core 搜索投影。");
            LibrarySearchButton.IsEnabled = true;
        }
        catch (Exception)
        {
            if (requestVersion != _librarySearchRequestVersion)
                return;
            LibraryResultsText.Text = "资料库搜索中断。";
            SetStatus(LibrarySearchStatusText, "资料库搜索：读取失败。", "error");
            LibraryResultsList.ItemsSource = Array.Empty<string>();
            LibrarySelectedDetailBorder.IsVisible = false;
            LibrarySearchButton.IsEnabled = true;
        }
    }

    private void OnLibraryResultSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (LibraryResultsList.SelectedItem is not LibraryResultRow selected)
        {
            LibrarySelectedDetailBorder.IsVisible = false;
            return;
        }
        ProjectSelectedLibraryResult(selected);
    }

    private void OnDetailListKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key != Key.Enter)
            return;

        if (ReferenceEquals(sender, LibraryResultsList))
        {
            ExecuteSelectedLibraryResult();
            e.Handled = true;
        }
        else if (ReferenceEquals(sender, SourceReaderMembersList))
        {
            OnReadSourceTransformClick(sender, new RoutedEventArgs());
            e.Handled = true;
        }
    }

    private void OnDetailListDoubleTapped(object? sender, TappedEventArgs e)
    {
        if (ReferenceEquals(sender, LibraryResultsList))
            ExecuteSelectedLibraryResult();
        else if (ReferenceEquals(sender, SourceReaderMembersList))
            OnReadSourceTransformClick(sender, new RoutedEventArgs());

        e.Handled = true;
    }

    private void OnEvidenceAnchorListKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key != Key.Enter)
            return;
        OnOpenEvidenceSourceClick(sender, new RoutedEventArgs());
        e.Handled = true;
    }

    private void OnEvidenceAnchorDoubleTapped(object? sender, TappedEventArgs e)
    {
        OnOpenEvidenceSourceClick(sender, new RoutedEventArgs());
        e.Handled = true;
    }

    private void ExecuteSelectedLibraryResult()
    {
        if (LibraryResultsList.SelectedItem is not LibraryResultRow selected)
            return;

        if (selected.Kind == "knowledge")
            OnOpenSelectedKnowledgeClick(this, new RoutedEventArgs());
        else
            OnOpenLibrarySourceClick(this, new RoutedEventArgs());
    }

    private void ProjectSelectedLibraryResult(LibraryResultRow selected)
    {
        _selectedLibraryResult = selected;
        LibrarySelectedDetailText.Text = selected.InspectorDetails;
        LibraryDetailKindText.Text = selected.KindLabel;
        LibraryDetailHeadText.Text = selected.Head;
        LibraryDetailStatusText.Text = selected.StatusLabel;
        LibraryDetailSourceText.Text = selected.SourceLabel;
        LibraryDetailKnowledgeText.Text = selected.Kind == "knowledge"
            ? $"knowledge_id：{(string.IsNullOrWhiteSpace(selected.KnowledgeId) ? "未暴露" : selected.KnowledgeId)}"
            : "Knowledge V3：此项为 transform，未读取知识投影。";
        LibraryDetailTransformText.Text = selected.Kind == "transform"
            ? $"transform_id：{(string.IsNullOrWhiteSpace(selected.TransformId) ? "未暴露" : selected.TransformId)}"
            : "Transform：此项为 knowledge，未从搜索结果推断转换记录。";
        LibraryDetailEngineText.Text = string.IsNullOrWhiteSpace(selected.Engine) ? "engine：未暴露" : $"engine：{selected.Engine}";
        if (selected.Kind == "transform")
            LibraryDetailBoundaryText.Text = "Transform 投影不是 Knowledge 接受状态。";
        else
            LibraryDetailBoundaryText.Text = "Knowledge 搜索命中仍需读取 Knowledge V3；字段缺失不推断。";
        LibrarySelectedDetailBorder.IsVisible = true;
        OpenLibrarySourceButton.IsEnabled = !string.IsNullOrWhiteSpace(selected.SourceId) && selected.SourceId != "—";
        SetInspectorProjection(
            "资料库结果",
            selected.InspectorDetails,
            selected.SourceId,
            selected.TransformId,
            selected.Status,
            "Library 字段来自 Core 搜索投影；未把提取结果升级为知识真相。",
            layer: selected.Kind == "transform"
                ? "Core projection · Transform search"
                : "Core projection · Knowledge search");
        UpdateInspectorActions();
    }

    private void OnBackToLibraryClick(object? sender, RoutedEventArgs e)
    {
        if (!_returnToLibraryAvailable || _selectedLibraryResult is null)
        {
            SourceReaderStatusText.Text = "没有可恢复的资料库选中结果。";
            return;
        }

        SetSection("library", "资料库");
        LibraryResultsList.SelectedItem = _selectedLibraryResult;
        ProjectSelectedLibraryResult(_selectedLibraryResult);
    }

    private void OnOpenLibrarySourceClick(object? sender, RoutedEventArgs e)
    {
        if (LibraryResultsList.SelectedItem is not LibraryResultRow selected
            || string.IsNullOrWhiteSpace(selected.SourceId)
            || selected.SourceId == "—")
        {
            LibraryResultsText.Text = "选中结果未暴露 source_id，无法读取来源成员。";
            return;
        }
        _selectedLibraryResult = selected;
        _sourceReaderReturnToKnowledgeAvailable = false;
        _sourceReaderReturnKnowledgeId = null;
        _returnToLibraryAvailable = true;
        BackToLibraryButton.IsEnabled = true;
        SourceReaderIdBox.Text = selected.SourceId.Trim();
        SetSection("source-reader", "导入阅读");
        OnReadSourceMembersClick(sender, e);
    }

    private void OnOpenSelectedKnowledgeClick(object? sender, RoutedEventArgs e)
    {
        if (LibraryResultsList.SelectedItem is not LibraryResultRow selected
            || selected.Kind != "knowledge")
        {
            LibraryResultsText.Text = "请选择一条知识结果后再读取 Knowledge 详情；提取结果不提供该投影。";
            return;
        }

        var knowledgeId = selected.KnowledgeId.Trim();
        if (knowledgeId.Length == 0)
        {
            LibraryResultsText.Text = "选中的知识结果未暴露 knowledge_id。";
            return;
        }

        KnowledgeIdBox.Text = knowledgeId;
        _knowledgeReturnToLibraryAvailable = true;
        BackToLibraryFromKnowledgeButton.IsEnabled = true;
        SetSection("knowledge", "知识详情");
        OnReadKnowledgeClick(sender, e);
    }

    private void OnOpenKnowledgeSourceClick(object? sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_activeKnowledgeSourceId) || _activeKnowledgeSourceId == "—")
        {
            KnowledgeResultsText.Text = "当前 Knowledge 未暴露 source_id，无法打开来源成员。";
            return;
        }

        _returnToLibraryAvailable = false;
        BackToLibraryButton.IsEnabled = false;
        _sourceReaderReturnKnowledgeId = KnowledgeIdBox.Text?.Trim();
        _sourceReaderReturnToKnowledgeAvailable = !string.IsNullOrWhiteSpace(_sourceReaderReturnKnowledgeId);
        SourceReaderIdBox.Text = _activeKnowledgeSourceId;
        SetSection("source-reader", "导入阅读");
        OnReadSourceMembersClick(sender, e);
    }

    private void OnBackToKnowledgeFromSourceClick(object? sender, RoutedEventArgs e)
    {
        if (!_sourceReaderReturnToKnowledgeAvailable || string.IsNullOrWhiteSpace(_sourceReaderReturnKnowledgeId))
        {
            SourceReaderResultsText.Text = "没有可恢复的 Knowledge 详情。";
            return;
        }

        KnowledgeIdBox.Text = _sourceReaderReturnKnowledgeId;
        _sourceReaderReturnToKnowledgeAvailable = false;
        _sourceReaderReturnKnowledgeId = null;
        SetSection("knowledge", "知识详情");
        OnReadKnowledgeClick(sender, e);
    }

    private void OnBackToLibraryFromKnowledgeClick(object? sender, RoutedEventArgs e)
    {
        if (!_knowledgeReturnToLibraryAvailable || _selectedLibraryResult is null)
        {
            KnowledgeResultsText.Text = "没有可恢复的资料库 Evidence Detail。";
            return;
        }

        SetSection("library", "资料库");
        LibrarySearchBox.Text = _librarySearchQuery ?? string.Empty;
        LibraryResultsList.SelectedItem = _selectedLibraryResult;
        ProjectSelectedLibraryResult(_selectedLibraryResult);
    }

    private void OnClosed(object? sender, EventArgs e)
    {
        // Supervisor shutdown: never leave an orphaned core process behind.
        _toastTimer.Stop();
        StopHomeHeroAmbientMotion();
        _deepTutor.Dispose();
        _supervisor?.Dispose();
    }

    private async void OnOpenLearningWorkbenchClick(object? sender, RoutedEventArgs e)
    {
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            CoreStatusText.Text = "学习工作台：核心未就绪";
            return;
        }
        var result = await _deepTutor.StartAsync();
        if (!result.ok)
        {
            CoreStatusText.Text = $"学习工作台：{result.detail}";
            return;
        }
        CoreStatusText.Text = _deepTutor.OpenBrowser()
            ? "学习工作台：已打开本地窗口"
            : $"学习工作台：已就绪（{_deepTutor.Url}）";
    }

    private void RefreshCaptureContextProjection()
    {
        var activeContext = _selectedCaptureContext ?? _latestCaptureContext;
        if (activeContext is null)
        {
            CaptureContextText.Text = "本次导入上下文：尚未形成 Core 来源。";
            HomeEvidenceText.Text = "本次会话尚无 Core 接收回执；不代表没有真实 Evidence。";
            HomeOpenCurrentSourceButton.IsEnabled = false;
            OpenLatestSourceButton.IsEnabled = false;
            OpenLatestJobButton.IsEnabled = false;
            LearningCaptureContextText.Text = "最近 Capture：尚未形成；未证明与当前学习项目关联。";
            OpenLearningCaptureSourceButton.IsEnabled = false;
            OpenLearningCaptureJobButton.IsEnabled = false;
            RefreshHomeLifecycleProjection();
            RefreshHomeReadingProjection();
            return;
        }
        CaptureContextText.Text = $"已保留 {_captureContexts.Count} 项导入上下文\n选中项：{activeContext.DisplayText}\n边界：source_id ↔ job_id ↔ file_name；未据此推断知识或学习关联。";
        HomeEvidenceText.Text = $"本次会话 Core 回执：{activeContext.FileName}\nsource_id={activeContext.SourceId} · job_id={activeContext.JobId} · 状态={activeContext.JobState}\n仅表示 Core 接收/任务回执；不代表 Knowledge 接受或 evidence anchor。";
        HomeOpenCurrentSourceButton.IsEnabled = !string.IsNullOrWhiteSpace(activeContext.SourceId);
        OpenLatestSourceButton.IsEnabled = !string.IsNullOrWhiteSpace(activeContext.SourceId);
        OpenLatestJobButton.IsEnabled = !string.IsNullOrWhiteSpace(activeContext.JobId)
            && activeContext.JobId != "未提交";
        LearningCaptureContextText.Text = $"最近 Capture：source_id={activeContext.SourceId} · job_id={activeContext.JobId} · 状态={activeContext.JobState}\n未证明与当前学习项目关联；学习来源仍以 Core learner.references 为准。";
        OpenLearningCaptureSourceButton.IsEnabled = OpenLatestSourceButton.IsEnabled;
        OpenLearningCaptureJobButton.IsEnabled = OpenLatestJobButton.IsEnabled;
        RefreshHomeLifecycleProjection();
        RefreshHomeReadingProjection();
    }

    private void OnCaptureContextSelected(object? sender, SelectionChangedEventArgs e)
    {
        _selectedCaptureContext = CaptureContextsList.SelectedItem as CaptureContextRow;
        RefreshCaptureContextProjection();
    }

    private void OnOpenLatestSourceClick(object? sender, RoutedEventArgs e)
    {
        var activeContext = _selectedCaptureContext ?? _latestCaptureContext;
        if (activeContext is null || string.IsNullOrWhiteSpace(activeContext.SourceId))
        {
            CaptureContextText.Text = "本次导入尚未形成可读取的 source_id。";
            return;
        }
        SourceReaderIdBox.Text = activeContext.SourceId;
        SetSection("source-reader", "导入阅读");
        OnReadSourceMembersClick(sender, e);
    }

    private void OnOpenHomeReadingClick(object? sender, RoutedEventArgs e)
    {
        OnOpenLatestSourceClick(sender, e);
    }

    private void RefreshHomeReadingProjection()
    {
        var activeContext = _selectedCaptureContext ?? _latestCaptureContext;
        if (activeContext is null || string.IsNullOrWhiteSpace(activeContext.SourceId))
        {
            HomeContinueReadingText.Text = "当前会话尚无可恢复来源；持久化阅读位置未接入。";
            HomeContinueReadingButton.IsEnabled = false;
            return;
        }

        HomeContinueReadingText.Text = $"当前会话来源：{activeContext.FileName}\nsource_id={activeContext.SourceId} · 状态={activeContext.JobState}\n仅当前会话，未宣称持久化阅读位置。";
        HomeContinueReadingButton.IsEnabled = true;
    }

    private void OnOpenLatestJobClick(object? sender, RoutedEventArgs e)
    {
        var activeContext = _selectedCaptureContext ?? _latestCaptureContext;
        if (activeContext is null
            || string.IsNullOrWhiteSpace(activeContext.JobId)
            || activeContext.JobId == "未提交")
        {
            CaptureContextText.Text = "本次导入尚未形成可查询的 job_id。";
            return;
        }
        JobLookupIdBox.Text = activeContext.JobId;
        SetSection("jobs", "任务");
        OnReadJobReceiptClick(sender, e);
    }

    private async void OnImportClick(object? sender, RoutedEventArgs e)
    {
        SetSection("capture", "捕获");
        var storage = TopLevel.GetTopLevel(this)?.StorageProvider;
        if (storage is null)
        {
            CoreStatusText.Text = "核心状态：文件选择器不可用";
            CaptureReceiptText.Text = "文件选择器不可用；未提交任何资料。";
            return;
        }

        var files = await storage.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "选择要导入的资料",
            AllowMultiple = true,
        });
        if (files.Count == 0)
        {
            CoreStatusText.Text = "核心状态：已取消资料选择";
            CaptureSelectionText.Text = "尚未选择资料。";
            CaptureReceiptText.Text = "已取消选择；未提交任何资料。";
            return;
        }
        CaptureSelectionText.Text = $"已选择 {files.Count} 个资料：{string.Join("、", files.Take(3).Select(file => file.Name))}{(files.Count > 3 ? " …" : string.Empty)}";
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            CoreStatusText.Text = $"核心状态：已选择 {files.Count} 个资料，但核心未就绪";
            CaptureReceiptText.Text = $"已选择 {files.Count} 个资料；Core 未就绪，未提交任何资料。";
            return;
        }

        var imported = 0;
        var executions = 0;
        var completed = 0;
        var failed = 0;
        try
        {
            foreach (var file in files)
            {
                await using var stream = await file.OpenReadAsync();
                using var buffer = new MemoryStream();
                await stream.CopyToAsync(buffer);
                var payload = JsonSerializer.Serialize(new
                {
                    name = file.Name,
                    content_base64 = Convert.ToBase64String(buffer.ToArray()),
                });
                using var response = await _supervisor.SendAsync(
                    HttpMethod.Post,
                    "/api/v1/imports",
                    new StringContent(payload, Encoding.UTF8, "application/json"));
                if (!response.IsSuccessStatusCode) continue;
                imported++;
                using var source = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
                var sourceId = source.RootElement.GetProperty("source_id").GetString();
                if (string.IsNullOrWhiteSpace(sourceId)) continue;
                var captureContext = new CaptureContextRow(file.Name, sourceId);
                _captureContexts.Add(captureContext);
                _latestCaptureContext = captureContext;
                _selectedCaptureContext = captureContext;
                CaptureContextsList.ItemsSource = _captureContexts.ToArray();
                CaptureContextsList.SelectedItem = captureContext;
                RefreshCaptureContextProjection();
                var jobId = $"desktop-import-{Guid.NewGuid():N}";
                var enqueue = JsonSerializer.Serialize(new { job_id = jobId, kind = JobKindFor(file.Name), input_ref = sourceId });
                using var queued = await _supervisor.SendAsync(
                    HttpMethod.Post,
                    "/api/v1/jobs",
                    new StringContent(enqueue, Encoding.UTF8, "application/json"));
                if (!queued.IsSuccessStatusCode)
                {
                    captureContext.JobState = "queue_failed";
                    RefreshCaptureContextProjection();
                    continue;
                }
                captureContext.JobId = jobId;
                captureContext.JobState = "queued";
                RefreshCaptureContextProjection();
                _sessionJobIds.Add(jobId);
            SetActivityDockSummary($"本次会话已登记 {_sessionJobIds.Count} 个任务 · 正在读取回执…");
                SetStatus(ActivityDockStatusText, "loading · Core 正在处理并读取任务回执。", "loading");
                var execution = new StringContent("{\"deadline_ms\":300000}", Encoding.UTF8, "application/json");
                using var started = await _supervisor.SendAsync(
                    HttpMethod.Post,
                    $"/api/v1/jobs/{Uri.EscapeDataString(jobId)}/executions",
                    execution,
                    new Dictionary<string, string> { ["idempotency-key"] = jobId });
                if (!started.IsSuccessStatusCode)
                {
                    captureContext.JobState = "execution_submit_failed";
                    RefreshCaptureContextProjection();
                    continue;
                }
                captureContext.JobState = "running";
                RefreshCaptureContextProjection();
                executions++;
                var state = await WaitForJobAsync(jobId);
                captureContext.JobState = string.IsNullOrWhiteSpace(state) ? "unknown" : state;
                RefreshCaptureContextProjection();
                if (state == "succeeded") completed++;
                else if (state is "failed" or "cancelled") failed++;
            }
        }
        catch (Exception)
        {
            CoreStatusText.Text = $"核心状态：导入中断，已提交 {imported}/{files.Count} 个资料";
            CaptureReceiptText.Text = $"导入中断；Core 已接收 {imported}/{files.Count} 个资料。转换与知识状态仍以任务回执为准。";
            foreach (var captureContext in _captureContexts.Where(context => context.JobState is "queued" or "running"))
                captureContext.JobState = "unknown";
            RefreshCaptureContextProjection();
            if (imported > 0)
                ShowToast("导入已中断，已保留部分 Core 回执", "info");
            return;
        }
        CoreStatusText.Text = $"核心状态：已导入 {imported}/{files.Count}，处理完成 {completed}/{executions}，失败 {failed}";
        CaptureReceiptText.Text = $"Core 已接收 {imported}/{files.Count} 个资料；任务完成 {completed}/{executions}，失败 {failed}。未据此推断知识已接受。";
        if (imported > 0)
            ShowToast($"已接收 {imported}/{files.Count} 项；任务状态见回执", failed == 0 ? "success" : "info");
        await RefreshJobsAsync();
        await RefreshWorkspaceSummaryAsync();
    }

    private async Task<string?> WaitForJobAsync(string jobId)
    {
        if (_supervisor is null) return null;
        for (var attempt = 0; attempt < 30; attempt++)
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Get,
                $"/api/v1/jobs/{Uri.EscapeDataString(jobId)}");
            if (!response.IsSuccessStatusCode) return null;
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (document.RootElement.TryGetProperty("state", out var state))
            {
                var value = state.GetString();
                if (value is "succeeded" or "failed" or "cancelled") return value;
            }
            await Task.Delay(200);
        }
        return null;
    }

    private static string JobKindFor(string name)
    {
        var extension = Path.GetExtension(name).ToLowerInvariant();
        return extension switch
        {
            ".pdf" => "pdf",
            ".png" or ".jpg" or ".jpeg" or ".tif" or ".tiff" or ".webp" or ".bmp" => "image",
            ".zip" => "archive",
            ".mp4" or ".wav" => "media",
            ".docx" or ".pptx" or ".xlsx" => "office",
            ".canvas" => "canvas",
            ".srt" or ".vtt" => "subtitles",
            ".html" or ".htm" => "html",
            _ => "text",
        };
    }

    private async void OnLearningClick(object? sender, RoutedEventArgs e)
    {
        var requestVersion = ++_learningRequestVersion;
        ++_reviewRequestVersion;
        if (!string.Equals(_activeSection, "learning", StringComparison.Ordinal))
        {
            _learningNavigationLoadInProgress = true;
            try
            {
                SetSection("learning", "学习");
            }
            finally
            {
                _learningNavigationLoadInProgress = false;
            }
        }
        LoadLearningButton.IsEnabled = false;
        ReviewOutcomeBox.Text = string.Empty;
        ReviewOutcomeBox.SelectedIndex = 0;
        ResetLearningProjectionForUnavailable(
            "学习路径：正在重新读取 Core 学习项目。",
            "旧学习投影已清除；等待当前读取结果。");
        SetStatus(LearningReviewStatusText, "尚未提交复习；提交结果由 Core 回执决定。", "empty");
        LearningReviewReceiptText.Text = "排程、下一次复习和 Mastery projection：尚未读取。";
        SetStatus(LearningStatusText, "学习路径：正在读取 Core", "loading");
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            CoreStatusText.Text = "学习路径：核心未就绪";
            ResetLearningProjectionForUnavailable(
                "学习路径：核心未就绪。",
                "请确认 Core 已连接后重新加载学习项目。");
            SetStatus(LearningStatusText, "学习路径：核心未就绪", "error");
            FinishLearningRequest(requestVersion);
            return;
        }
        try
        {
            using var response = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/learning/items");
            if (requestVersion != _learningRequestVersion)
                return;
            if (!response.IsSuccessStatusCode)
            {
                var permissionDenied = response.StatusCode is System.Net.HttpStatusCode.Unauthorized
                    or System.Net.HttpStatusCode.Forbidden;
                CoreStatusText.Text = permissionDenied
                    ? "学习路径：Core 拒绝读取队列"
                    : "学习路径：队列读取失败";
                ResetLearningProjectionForUnavailable(
                    permissionDenied
                        ? "学习路径：Core 拒绝当前访问权限。"
                        : $"学习路径：队列读取失败（HTTP {(int)response.StatusCode}）。",
                    "请检查会话或权限范围，然后重新加载学习项目。");
                SetStatus(
                    LearningStatusText,
                    permissionDenied
                        ? "学习路径：Core 拒绝当前访问权限，请检查会话或权限范围。"
                        : "学习路径：队列读取失败，可重新加载或检查 Core 状态。",
                    permissionDenied ? "permission" : "error");
                FinishLearningRequest(requestVersion);
                return;
            }
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if (requestVersion != _learningRequestVersion)
                return;
            var count = document.RootElement.GetProperty("count").GetInt32();
            var learningStateAvailable = false;
            if (count > 0)
            {
                var items = document.RootElement.GetProperty("items");
                var queueRows = new List<LearningQueueRow>();
                JsonElement first = default;
                foreach (var item in items.EnumerateArray())
                {
                    var itemKey = item.TryGetProperty("item_key", out var itemKeyValue)
                        ? itemKeyValue.GetString()
                        : null;
                    if (string.IsNullOrWhiteSpace(itemKey))
                        continue;
                    var queueNextReview = item.TryGetProperty("next_review", out var dueValue)
                        && dueValue.ValueKind != JsonValueKind.Null
                        ? dueValue.GetString() ?? "未排程"
                        : "未排程";
                    queueRows.Add(new LearningQueueRow(itemKey, queueNextReview));
                    if (first.ValueKind == JsonValueKind.Undefined
                        && (string.IsNullOrWhiteSpace(_selectedLearningItemKey)
                            || string.Equals(_selectedLearningItemKey, itemKey, StringComparison.Ordinal)))
                    {
                        first = item;
                        _selectedLearningItemKey = itemKey;
                    }
                }
                if (first.ValueKind == JsonValueKind.Undefined && queueRows.Count > 0)
                {
                    _selectedLearningItemKey = queueRows[0].ItemKey;
                    first = items.EnumerateArray().First(item =>
                        string.Equals(item.GetProperty("item_key").GetString(), _selectedLearningItemKey, StringComparison.Ordinal));
                }
                _hydratingLearningQueue = true;
                LearningQueueList.ItemsSource = queueRows;
                LearningQueueList.SelectedItem = queueRows.FirstOrDefault(row =>
                    string.Equals(row.ItemKey, _selectedLearningItemKey, StringComparison.Ordinal));
                _hydratingLearningQueue = false;
                _activeLearningItem = first.GetProperty("item_key").GetString();
                _activeReviewEventId = null;
                _activeExposureId = null;
                _activeAssessmentId = null;
                _activeKnowledgeId = null;
                _activeKnowledgeVersion = null;
                var nextReview = first.TryGetProperty("next_review", out var due)
                    && due.ValueKind != JsonValueKind.Null ? due.GetString() : "未排程";
                var referenceText = "来源版本：未记录";
                var learningProjectionText = "FSRS/Mastery：未暴露";
                string? activeKnowledgeId = null;
                using (var stateResponse = await _supervisor.SendAsync(
                    HttpMethod.Get, $"/api/v1/learning/items/{Uri.EscapeDataString(_activeLearningItem ?? string.Empty)}/state"))
                {
                    if (requestVersion != _learningRequestVersion)
                        return;
                    if (stateResponse.IsSuccessStatusCode)
                    {
                        learningStateAvailable = true;
                        using var state = JsonDocument.Parse(await stateResponse.Content.ReadAsStringAsync());
                        if (requestVersion != _learningRequestVersion)
                            return;
                        // Provenance lives on the learner side of the Core projection
                        // (learner.references). Reading it from the document root
                        // reported "未记录" for every item even when references existed.
                        if (state.RootElement.TryGetProperty("learner", out var learner)
                            && learner.ValueKind == JsonValueKind.Object
                            && learner.TryGetProperty("references", out var references)
                            && references.ValueKind == JsonValueKind.Array)
                        {
                            var current = new List<string>();
                            var superseded = new List<string>();
                            foreach (var reference in references.EnumerateArray())
                            {
                                if (!reference.TryGetProperty("knowledge_id", out var id)) continue;
                                var knowledgeId = id.GetString();
                                if (string.IsNullOrWhiteSpace(knowledgeId)) continue;
                                // Only an explicit active=true is a current source version.
                                // Anything else is shown as superseded rather than silently
                                // promoted to current.
                                var isActive = reference.TryGetProperty("active", out var active)
                                    && active.ValueKind == JsonValueKind.True;
                                if (isActive && activeKnowledgeId is null) activeKnowledgeId = knowledgeId;
                                (isActive ? current : superseded).Add(knowledgeId);
                            }
                            var lines = new List<string>();
                            if (current.Count > 0) lines.Add($"当前来源版本：{string.Join(", ", current)}");
                            if (superseded.Count > 0) lines.Add($"已被替代版本：{string.Join(", ", superseded)}");
                            if (lines.Count > 0) referenceText = string.Join("\n", lines);

                            var scheduledEvents = ReadDisplayValue(learner, "scheduled_events");
                            var unscheduledEvents = ReadDisplayValue(learner, "unscheduled_events");
                            var latestReviewText = "未暴露";
                            if (learner.TryGetProperty("latest_review", out var latestReview)
                                && latestReview.ValueKind == JsonValueKind.Object)
                            {
                                latestReviewText =
                                    $"authority={ReadDisplayValue(latestReview, "schedule_authority")} · " +
                                    $"state={ReadDisplayValue(latestReview, "schedule_state")}";
                                var mastery = latestReview.TryGetProperty("mastery_projection", out var projection)
                                    && projection.ValueKind == JsonValueKind.Object
                                    ? $"closed={ReadDisplayValue(projection, "closed")} · status={ReadDisplayValue(projection, "status")}"
                                    : "未暴露";
                                learningProjectionText =
                                    $"FSRS：{latestReviewText}\nMastery projection：{mastery}\n" +
                                    $"排程事件：已排程 {scheduledEvents} · 未排程 {unscheduledEvents}";
                            }
                        }
                    }
                    else
                    {
                        referenceText = "来源状态读取失败；未推断当前来源版本。";
                    }
                }
                _activeKnowledgeId = activeKnowledgeId;
                LearningEvidenceText.Text = referenceText;
                LearningOriginalText.Text = string.IsNullOrWhiteSpace(activeKnowledgeId)
                    ? "原件正文未从学习投影直接暴露。"
                    : "原件正文未从学习投影直接暴露；请从原件阅读按来源投影查看。";
                OpenLearningKnowledgeButton.IsEnabled = !string.IsNullOrWhiteSpace(activeKnowledgeId);
                var assessmentText = "Assessment：未生成";
                var assessmentReady = false;
                if (!string.IsNullOrWhiteSpace(activeKnowledgeId))
                {
                    async Task<bool> BindAssessmentAsync(HttpResponseMessage response)
                    {
                        if (requestVersion != _learningRequestVersion) return false;
                        if (!response.IsSuccessStatusCode) return false;
                        using var assessment = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
                        if (requestVersion != _learningRequestVersion) return false;
                        if (!assessment.RootElement.TryGetProperty("knowledge_id", out var returnedKnowledge)
                            || !string.Equals(returnedKnowledge.GetString(), activeKnowledgeId, StringComparison.Ordinal))
                        {
                            return false;
                        }
                        _activeAssessmentId = assessment.RootElement.GetProperty("assessment_id").GetString();
                        _activeKnowledgeVersion = assessment.RootElement.GetProperty("knowledge_version").GetString();
                        var question = assessment.RootElement.GetProperty("question").GetString() ?? "";
                        var content = assessment.RootElement.GetProperty("content").GetString() ?? "";
                        assessmentText = $"{question}\n内容：{content}";
                        return !string.IsNullOrWhiteSpace(_activeAssessmentId)
                            && !string.IsNullOrWhiteSpace(_activeKnowledgeVersion);
                    }

                    using var assessmentResponse = await _supervisor.SendAsync(
                        HttpMethod.Get,
                        $"/api/v1/learning/items/{Uri.EscapeDataString(_activeLearningItem ?? string.Empty)}/assessment");
                    if (requestVersion != _learningRequestVersion)
                        return;
                    assessmentReady = await BindAssessmentAsync(assessmentResponse);
                    if (!assessmentReady
                        && (assessmentResponse.StatusCode == System.Net.HttpStatusCode.NotFound
                            || assessmentResponse.IsSuccessStatusCode))
                    {
                        if (requestVersion != _learningRequestVersion)
                            return;
                        using var createdAssessment = await _supervisor.SendAsync(
                            HttpMethod.Post,
                            $"/api/v1/learning/items/{Uri.EscapeDataString(_activeLearningItem ?? string.Empty)}/assessment",
                            new StringContent(JsonSerializer.Serialize(new { knowledge_id = activeKnowledgeId }), Encoding.UTF8, "application/json"));
                        if (requestVersion != _learningRequestVersion)
                            return;
                        assessmentReady = await BindAssessmentAsync(createdAssessment);
                    }
                }
                if (!assessmentReady && !string.IsNullOrWhiteSpace(activeKnowledgeId))
                    assessmentText = "Assessment 未就绪；未启用回答提交。";
                LearningVersionText.Text = $"knowledge_id={_activeKnowledgeId ?? "未暴露"}\nknowledge_version={_activeKnowledgeVersion ?? "未生成"}\nassessment_id={_activeAssessmentId ?? "未生成"}";
                var readbackText = "学习记录：未读回";
                using (var historyResponse = await _supervisor.SendAsync(
                    HttpMethod.Get,
                    $"/api/v1/learning/events/{Uri.EscapeDataString(_activeLearningItem ?? string.Empty)}"))
                {
                    if (requestVersion != _learningRequestVersion)
                        return;
                    if (historyResponse.IsSuccessStatusCode)
                    {
                        try
                        {
                            using var history = JsonDocument.Parse(await historyResponse.Content.ReadAsStringAsync());
                            if (requestVersion != _learningRequestVersion)
                                return;
                            if (history.RootElement.TryGetProperty("events", out var events)
                                && events.ValueKind == JsonValueKind.Array
                                && events.GetArrayLength() > 0)
                            {
                                var latest = events[events.GetArrayLength() - 1];
                                if (latest.TryGetProperty("outcome", out var outcome)
                                    && outcome.ValueKind == JsonValueKind.String
                                    && !string.IsNullOrWhiteSpace(outcome.GetString()))
                                {
                                    using var outcomeDocument = JsonDocument.Parse(outcome.GetString()!);
                                    var savedAnswerText = outcomeDocument.RootElement.TryGetProperty("answer", out var answerValue)
                                        && answerValue.ValueKind == JsonValueKind.String
                                        ? answerValue.GetString()
                                        : null;
                                    var savedAnswer = !string.IsNullOrWhiteSpace(savedAnswerText);
                                    if (!string.IsNullOrWhiteSpace(savedAnswerText))
                                        LearningAnswerBox.Text = savedAnswerText;
                                    var projectionOpen = outcomeDocument.RootElement.TryGetProperty("mastery_projection", out var projection)
                                        && projection.ValueKind == JsonValueKind.Object
                                        && projection.TryGetProperty("closed", out var closed)
                                        && closed.ValueKind == JsonValueKind.False;
                                    readbackText = savedAnswer && projectionOpen
                                        ? "已保存回答；Mastery projection 未闭合"
                                        : savedAnswer ? "已保存回答" : "学习记录已读回";
                                }
                            }
                        }
                        catch (JsonException)
                        {
                            readbackText = "学习记录读取失败";
                        }
                    }
                    else
                    {
                        readbackText = "学习记录读取失败";
                    }
                }
                if (requestVersion != _learningRequestVersion)
                    return;
                LearningMemoryText.Text = readbackText;
                LearningItemText.Text = $"{assessmentText}\n待复习项目：{_activeLearningItem}\n下次复习：{nextReview}\n{learningProjectionText}\n{referenceText}\n{readbackText}";
                SetInspectorProjection(
                    _activeLearningItem ?? "学习项目",
                    $"下次复习：{nextReview}\n{learningProjectionText}\n{referenceText}\nAssessment：{_activeAssessmentId ?? "未生成"}\n来自 Core 学习与 Assessment 投影。",
                    source: null,
                    version: _activeKnowledgeVersion,
                    status: null,
                    boundary: "学习来源仅显示 Core learner.references 与 Assessment 已暴露字段；assessment_id 不是对象状态，未暴露引用位置不推断。",
                    layer: "Core projection · Learning/Assessment");
                LearningAnswerBox.IsEnabled = assessmentReady;
                ReviewOutcomeBox.IsEnabled = assessmentReady;
                ReviewAgainButton.IsEnabled = assessmentReady;
                ReviewHardButton.IsEnabled = assessmentReady;
                ReviewGoodButton.IsEnabled = assessmentReady;
                ReviewEasyButton.IsEnabled = assessmentReady;
                SubmitReviewButton.IsEnabled = assessmentReady;
            }
            else
            {
                LearningEmptyActions.IsVisible = true;
                _activeLearningItem = null;
                _activeReviewEventId = null;
                _activeExposureId = null;
                _activeAssessmentId = null;
                _activeKnowledgeId = null;
                _activeKnowledgeVersion = null;
                LearningItemText.Text = "当前没有待复习项目";
                LearningEvidenceText.Text = "尚未载入 Core 学习来源。";
                LearningOriginalText.Text = "原件正文未从学习投影直接暴露。";
                LearningVersionText.Text = "尚未生成";
                LearningMemoryText.Text = "学习记录：未读回";
                OpenLearningKnowledgeButton.IsEnabled = false;
                LearningAnswerBox.IsEnabled = false;
                ReviewOutcomeBox.IsEnabled = false;
                ReviewAgainButton.IsEnabled = false;
                ReviewHardButton.IsEnabled = false;
                ReviewGoodButton.IsEnabled = false;
                ReviewEasyButton.IsEnabled = false;
                SubmitReviewButton.IsEnabled = false;
                await RefreshWorkspaceSummaryAsync();
            }
            CoreStatusText.Text = count == 0
                ? "学习路径：当前没有待复习项目"
                : $"学习路径：{count} 个项目可复习";
            var learningStatus = count == 0
                ? "学习路径：当前没有待复习项目"
                : !learningStateAvailable
                    ? "学习路径：队列已读取；来源状态读取失败。"
                : string.IsNullOrWhiteSpace(_activeKnowledgeId)
                    ? "学习路径：队列已读取；当前来源版本未暴露。"
                : string.IsNullOrWhiteSpace(_activeAssessmentId)
                    ? "学习路径：队列已读取；Assessment 未就绪。"
                    : $"学习路径：已读取 {count} 个项目；当前项目状态来自 Core。";
            var learningSemanticState = count == 0
                ? "empty"
                : !learningStateAvailable
                    ? "error"
                : string.IsNullOrWhiteSpace(_activeKnowledgeId) || string.IsNullOrWhiteSpace(_activeAssessmentId)
                    ? "info"
                    : "success";
            SetStatus(LearningStatusText, learningStatus, learningSemanticState);
            FinishLearningRequest(requestVersion);
        }
        catch (Exception)
        {
            if (requestVersion != _learningRequestVersion)
                return;
            CoreStatusText.Text = "学习路径：队列读取中断";
            ResetLearningProjectionForUnavailable(
                "学习路径：读取中断；未保留上一条学习投影。",
                "请重新加载复习项目，或到设置页检查 Core 状态。");
            SetStatus(LearningStatusText, "学习路径：队列读取中断", "error");
            FinishLearningRequest(requestVersion);
        }
    }

    private void SetReviewRating(int rating)
    {
        if (!ReviewOutcomeBox.IsEnabled)
            return;
        _activeReviewRating = rating;
        // FSRS self-rating is independent from the Core assessment result.
        // Do not silently rewrite the user's correctness choice when a grade
        // button is pressed; both fields must remain explicit in the receipt.
        ReviewAgainButton.Classes.Set("selected", rating == 1);
        ReviewHardButton.Classes.Set("selected", rating == 2);
        ReviewGoodButton.Classes.Set("selected", rating == 3);
        ReviewEasyButton.Classes.Set("selected", rating == 4);
        SetStatus(LearningReviewStatusText, $"已选择 FSRS {rating}；请单独选择回答结果后提交。", "info");
    }

    private void OnReviewAgainClick(object? sender, RoutedEventArgs e) => SetReviewRating(1);

    private void OnReviewHardClick(object? sender, RoutedEventArgs e) => SetReviewRating(2);

    private void OnReviewGoodClick(object? sender, RoutedEventArgs e) => SetReviewRating(3);

    private void OnReviewEasyClick(object? sender, RoutedEventArgs e) => SetReviewRating(4);

    private bool IsCurrentReviewSubmission(
        long requestVersion,
        string itemKey,
        string assessmentId,
        string? knowledgeId,
        string? knowledgeVersion,
        string eventId,
        string exposureId)
        => requestVersion == _reviewRequestVersion
            && string.Equals(_activeLearningItem, itemKey, StringComparison.Ordinal)
            && string.Equals(_activeAssessmentId, assessmentId, StringComparison.Ordinal)
            && string.Equals(_activeKnowledgeId, knowledgeId, StringComparison.Ordinal)
            && string.Equals(_activeKnowledgeVersion, knowledgeVersion, StringComparison.Ordinal)
            && string.Equals(_activeReviewEventId, eventId, StringComparison.Ordinal)
            && string.Equals(_activeExposureId, exposureId, StringComparison.Ordinal);

    private async void OnSubmitReviewClick(object? sender, RoutedEventArgs e)
    {
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0 || string.IsNullOrWhiteSpace(_activeLearningItem)
            || string.IsNullOrWhiteSpace(_activeAssessmentId))
        {
            CoreStatusText.Text = "学习路径：请先载入复习项目";
            SetStatus(LearningReviewStatusText, "复习提交失败：请先载入复习项目。", "error");
            return;
        }
        var answer = LearningAnswerBox.Text?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(answer))
        {
            CoreStatusText.Text = "学习路径：请输入回答后再提交";
            SetStatus(LearningReviewStatusText, "复习提交失败：请输入回答。", "error");
            return;
        }
        if (ReviewOutcomeBox.SelectedIndex is not (1 or 2))
        {
            CoreStatusText.Text = "学习路径：请选择回答结果";
            SetStatus(LearningReviewStatusText, "复习提交失败：请选择回答结果。", "error");
            return;
        }
        var correct = ReviewOutcomeBox.SelectedIndex == 1;
        var rating = _activeReviewRating ?? (correct ? 3 : 1);
        if ((correct && rating == 1) || (!correct && rating >= 3))
        {
            CoreStatusText.Text = "学习路径：回答结果与 FSRS 评分组合不一致";
            SetStatus(LearningReviewStatusText, "复习提交失败：请调整回答结果或 FSRS 评分。", "error");
            return;
        }
        SubmitReviewButton.IsEnabled = false;
        SetStatus(LearningReviewStatusText, "复习提交中：正在读取 Core 回执。", "loading");
        // Retry stability: the ids are allocated once per exposure and reused until
        // the review is accepted, so a failed submit is not recorded twice.
        _activeReviewEventId ??= $"desktop-{Guid.NewGuid():N}";
        _activeExposureId ??= $"desktop-exposure-{Guid.NewGuid():N}";
        var reviewRequestVersion = ++_reviewRequestVersion;
        var submittedItemKey = _activeLearningItem;
        var submittedAssessmentId = _activeAssessmentId;
        var submittedKnowledgeId = _activeKnowledgeId;
        var submittedKnowledgeVersion = _activeKnowledgeVersion;
        var submittedEventId = _activeReviewEventId;
        var submittedExposureId = _activeExposureId;
        if (submittedItemKey is null || submittedAssessmentId is null || submittedEventId is null || submittedExposureId is null)
        {
            SubmitReviewButton.IsEnabled = true;
            SetStatus(LearningReviewStatusText, "复习提交失败：当前项目身份未完整暴露。", "error");
            return;
        }
        var payload = JsonSerializer.Serialize(new
        {
            item_key = submittedItemKey,
            client_event_id = submittedEventId,
            correct,
            rating,
            answer,
            assessment_id = submittedAssessmentId,
            knowledge_version = submittedKnowledgeVersion,
            rating_version = "desktop-v1",
            exposure_id = submittedExposureId,
        });
        try
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Post,
                "/api/v1/learning/reviews",
                new StringContent(payload, Encoding.UTF8, "application/json"));
            if (!IsCurrentReviewSubmission(
                    reviewRequestVersion,
                    submittedItemKey,
                    submittedAssessmentId,
                    submittedKnowledgeId,
                    submittedKnowledgeVersion,
                    submittedEventId,
                    submittedExposureId))
                return;
            if (response.IsSuccessStatusCode)
            {
                var savedAnswer = false;
                var masteryProjectionOpen = false;
                var scheduleAuthority = "未暴露";
                var scheduleState = "未暴露";
                var nextReview = "未暴露";
                var nextReviewDays = "未暴露";
                try
                {
                    using var reviewResponse = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
                    var reviewRoot = reviewResponse.RootElement;
                    savedAnswer = reviewResponse.RootElement.TryGetProperty("answer", out var answerValue)
                        && answerValue.ValueKind == JsonValueKind.String
                        && !string.IsNullOrWhiteSpace(answerValue.GetString());
                    scheduleAuthority = ReadDisplayValue(reviewRoot, "schedule_authority");
                    scheduleState = ReadDisplayValue(reviewRoot, "schedule_state");
                    nextReview = ReadDisplayValue(reviewRoot, "next_review");
                    nextReviewDays = ReadDisplayValue(reviewRoot, "next_review_days");
                    if (reviewResponse.RootElement.TryGetProperty("mastery_projection", out var projection)
                        && projection.ValueKind == JsonValueKind.Object
                        && projection.TryGetProperty("closed", out var closed))
                    {
                        masteryProjectionOpen = closed.ValueKind == JsonValueKind.False;
                    }
                }
                catch (JsonException)
                {
                    // The event is already persisted; keep the UI status conservative.
                }
                LearningReviewReceiptText.Text =
                    $"排程 authority：{scheduleAuthority} · state：{scheduleState}\n" +
                    $"下一次复习：{nextReview} · days：{nextReviewDays}\n" +
                    $"回答回执：{(savedAnswer ? "已由 Core 保存" : "未暴露")} · " +
                    $"Mastery projection：{(masteryProjectionOpen ? "未闭合" : "按 Core 回执显示")}";
                CoreStatusText.Text = savedAnswer && masteryProjectionOpen
                    ? "学习路径：复习已记录（回答已保存；Mastery projection 未闭合）"
                    : "学习路径：复习已记录";
                SetStatus(
                    LearningReviewStatusText,
                    savedAnswer && masteryProjectionOpen
                        ? "复习已记录；回答已保存，但 Mastery projection 未闭合。"
                        : "复习已记录；知识接受状态仍由 Core projection 决定。",
                    "success");
                ShowToast("复习结果已由 Core 记录");
                // The exposure is closed: the next one must carry fresh ids.
                _activeReviewEventId = null;
                _activeExposureId = null;
                _activeAssessmentId = null;
                _activeKnowledgeId = null;
                _activeKnowledgeVersion = null;
                LearningAnswerBox.Text = string.Empty;
                ReviewOutcomeBox.SelectedIndex = 0;
                ReviewAgainButton.IsEnabled = false;
                ReviewHardButton.IsEnabled = false;
                ReviewGoodButton.IsEnabled = false;
                ReviewEasyButton.IsEnabled = false;
                SubmitReviewButton.IsEnabled = false;
                _activeReviewRating = null;
            }
            else
            {
                SubmitReviewButton.IsEnabled = true;
                var permissionDenied = response.StatusCode is System.Net.HttpStatusCode.Unauthorized
                    or System.Net.HttpStatusCode.Forbidden;
                SetStatus(
                    LearningReviewStatusText,
                    permissionDenied
                        ? "复习提交被 Core 拒绝：请检查会话或权限范围。"
                        : $"复习提交失败：Core HTTP {(int)response.StatusCode}。",
                    permissionDenied ? "permission" : "error");
            }
        }
        catch (Exception)
        {
            if (!IsCurrentReviewSubmission(
                    reviewRequestVersion,
                    submittedItemKey,
                    submittedAssessmentId,
                    submittedKnowledgeId,
                    submittedKnowledgeVersion,
                    submittedEventId,
                    submittedExposureId))
                return;
            SubmitReviewButton.IsEnabled = true;
            CoreStatusText.Text = "学习路径：复习提交中断";
            SetStatus(LearningReviewStatusText, "复习提交中断；请以 Core 回执为准。", "error");
        }
    }
}

public sealed class LibraryResultRow
{
    public string Kind { get; }
    public string KnowledgeId { get; }
    public string SourceId { get; }
    public string TransformId { get; }
    public string Status { get; }
    public string Active { get; }
    public string Engine { get; }
    public string Head { get; }
    public string KindLabel => Kind == "knowledge" ? "KNOWLEDGE" : "TRANSFORM";
    public string StatusLabel => Kind == "transform"
        ? "Knowledge 状态：不适用"
        : $"status={Status} · active={Active}";
    public string SourceLabel => string.IsNullOrWhiteSpace(SourceId)
        ? "source_id：未暴露"
        : $"source_id：{SourceId}";
    public string DisplayText => Kind == "transform"
        ? $"提取文本命中 · {SourceId}: {Head} · transform_id={TransformId} · engine={Engine}"
        : $"知识 · {KnowledgeId}: {Head} · status={Status} · active={Active}";
    public string InspectorDetails => Kind == "transform"
        ? $"类型：transform\nTransform：{TransformId}\n来源：{SourceId}\n引擎：{Engine}\n标题：{Head}\nTransform 投影不是 Knowledge 接受状态。\n来自 Core 搜索投影；未把结果文本升级为新的知识真相。"
        : $"类型：knowledge\nKnowledge：{KnowledgeId}\n来源：{SourceId}\n状态：{Status}\nActive：{Active}\n引擎：{Engine}\n标题：{Head}\n来自 Core 搜索投影；未把结果文本升级为新的知识真相。";

    public LibraryResultRow(string kind, string knowledgeId, string sourceId, string transformId, string status, string active, string engine, string head)
    {
        Kind = kind;
        KnowledgeId = knowledgeId;
        SourceId = sourceId;
        TransformId = transformId;
        Status = status;
        Active = active;
        Engine = engine;
        Head = head;
    }

    public override string ToString() => DisplayText;
}

public sealed class EvidenceAnchorRow
{
    public string AnchorId { get; }
    public string SourceId { get; }
    public string RawSha256 { get; }
    public string SourceRevision { get; }
    public string Locator { get; }
    public string DisplayText => $"{AnchorId} · source={SourceId} · revision={SourceRevision}";
    public string DetailText =>
        $"anchor_id={AnchorId}\nsource_id={SourceId}\nraw_sha256={RawSha256}\nsource_revision={SourceRevision}\nlocator={Locator}\n" +
        "Evidence anchor 仅提供来源定位，不包含原文正文。";

    public EvidenceAnchorRow(string anchorId, string sourceId, string rawSha256, string sourceRevision, string locator)
    {
        AnchorId = anchorId;
        SourceId = sourceId;
        RawSha256 = rawSha256;
        SourceRevision = sourceRevision;
        Locator = locator;
    }

    public override string ToString() => DisplayText;
}

using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;

namespace ArcheAxis.Desktop;

public partial class MainWindow : Window
{
    private CoreSupervisor? _supervisor;
    private readonly DeepTutorSupervisor _deepTutor = DeepTutorSupervisor.CreateFromEnvironment();
    private string? _activeLearningItem;

    public MainWindow()
    {
        InitializeComponent();
        Title = "ArcheAxis Learning Workspace (vNext) — core offline";
        Loaded += OnLoaded;
        Closed += OnClosed;
    }

    private async void OnLoaded(object? sender, RoutedEventArgs e)
    {
        // Only start and authenticate our own Core; never adopt a shared service.
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
            await RefreshWorkspaceSummaryAsync();
        }
        else
        {
            Title = $"ArcheAxis Learning Workspace (vNext) — core offline ({result.detail})";
            CoreStatusText.Text = "核心状态：离线";
        }
    }

    private async Task RefreshWorkspaceSummaryAsync()
    {
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
            return;
        try
        {
            using var response = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/workspaces/info");
            if (!response.IsSuccessStatusCode)
                return;
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            var sources = ReadInt(document.RootElement, "sources");
            var anchors = ReadInt(document.RootElement, "anchors");
            using var learningResponse = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/learning/items");
            var learning = 0;
            if (learningResponse.IsSuccessStatusCode)
            {
                using var learningDocument = JsonDocument.Parse(await learningResponse.Content.ReadAsStringAsync());
                learning = ReadInt(learningDocument.RootElement, "count");
            }
            SourcesCountText.Text = sources.ToString();
            LearningCountText.Text = learning.ToString();
            AnchorsCountText.Text = anchors.ToString();
        }
        catch (Exception)
        {
            CoreStatusText.Text = "核心状态：已连接 · 状态读取失败";
        }
    }

    private static int ReadInt(JsonElement root, string name)
    {
        return root.TryGetProperty(name, out var value) && value.TryGetInt32(out var count)
            ? count
            : 0;
    }

    private void OnClosed(object? sender, EventArgs e)
    {
        // Supervisor shutdown: never leave an orphaned core process behind.
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

    private async void OnImportClick(object? sender, RoutedEventArgs e)
    {
        var storage = TopLevel.GetTopLevel(this)?.StorageProvider;
        if (storage is null)
        {
            CoreStatusText.Text = "核心状态：文件选择器不可用";
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
            return;
        }
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            CoreStatusText.Text = $"核心状态：已选择 {files.Count} 个资料，但核心未就绪";
            return;
        }

        var imported = 0;
        var executions = 0;
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
                var jobId = $"desktop-import-{Guid.NewGuid():N}";
                var enqueue = JsonSerializer.Serialize(new { job_id = jobId, kind = JobKindFor(file.Name), input_ref = sourceId });
                using var queued = await _supervisor.SendAsync(
                    HttpMethod.Post,
                    "/api/v1/jobs",
                    new StringContent(enqueue, Encoding.UTF8, "application/json"));
                if (!queued.IsSuccessStatusCode) continue;
                var execution = new StringContent("{\"deadline_ms\":300000}", Encoding.UTF8, "application/json");
                using var started = await _supervisor.SendAsync(
                    HttpMethod.Post,
                    $"/api/v1/jobs/{Uri.EscapeDataString(jobId)}/executions",
                    execution,
                    new Dictionary<string, string> { ["idempotency-key"] = jobId });
                if (started.IsSuccessStatusCode) executions++;
            }
        }
        catch (Exception)
        {
            CoreStatusText.Text = $"核心状态：导入中断，已提交 {imported}/{files.Count} 个资料";
            return;
        }
        CoreStatusText.Text = $"核心状态：已导入 {imported}/{files.Count}，已启动 {executions} 个处理任务";
        await RefreshWorkspaceSummaryAsync();
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
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        {
            CoreStatusText.Text = "学习路径：核心未就绪";
            return;
        }
        try
        {
            using var response = await _supervisor.SendAsync(HttpMethod.Get, "/api/v1/learning/items");
            if (!response.IsSuccessStatusCode)
            {
                CoreStatusText.Text = "学习路径：队列读取失败";
                return;
            }
            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            var count = document.RootElement.GetProperty("count").GetInt32();
            if (count > 0)
            {
                var first = document.RootElement.GetProperty("items")[0];
                _activeLearningItem = first.GetProperty("item_key").GetString();
                var nextReview = first.TryGetProperty("next_review", out var due)
                    && due.ValueKind != JsonValueKind.Null ? due.GetString() : "未排程";
                var referenceText = "来源版本：未记录";
                using (var stateResponse = await _supervisor.SendAsync(
                    HttpMethod.Get, $"/api/v1/learning/items/{Uri.EscapeDataString(_activeLearningItem ?? string.Empty)}/state"))
                {
                    if (stateResponse.IsSuccessStatusCode)
                    {
                        using var state = JsonDocument.Parse(await stateResponse.Content.ReadAsStringAsync());
                        if (state.RootElement.TryGetProperty("references", out var references)
                            && references.ValueKind == JsonValueKind.Array)
                        {
                            var ids = new System.Collections.Generic.List<string>();
                            foreach (var reference in references.EnumerateArray())
                            {
                                if (reference.TryGetProperty("knowledge_id", out var id))
                                    ids.Add(id.GetString() ?? string.Empty);
                            }
                            ids.RemoveAll(string.IsNullOrWhiteSpace);
                            if (ids.Count > 0) referenceText = $"来源版本：{string.Join(", ", ids)}";
                        }
                    }
                }
                LearningItemText.Text = $"待复习项目：{_activeLearningItem}\n下次复习：{nextReview}\n{referenceText}";
                LearningAnswerBox.IsEnabled = true;
                ReviewOutcomeBox.IsEnabled = true;
                SubmitReviewButton.IsEnabled = true;
            }
            else
            {
                _activeLearningItem = null;
                LearningItemText.Text = "当前没有待复习项目";
                LearningAnswerBox.IsEnabled = false;
                ReviewOutcomeBox.IsEnabled = false;
                SubmitReviewButton.IsEnabled = false;
                await RefreshWorkspaceSummaryAsync();
            }
            CoreStatusText.Text = count == 0
                ? "学习路径：当前没有待复习项目"
                : $"学习路径：{count} 个项目可复习";
        }
        catch (Exception)
        {
            CoreStatusText.Text = "学习路径：队列读取中断";
        }
    }

    private async void OnSubmitReviewClick(object? sender, RoutedEventArgs e)
    {
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0 || string.IsNullOrWhiteSpace(_activeLearningItem))
        {
            CoreStatusText.Text = "学习路径：请先载入复习项目";
            return;
        }
        var answer = LearningAnswerBox.Text?.Trim() ?? string.Empty;
        if (ReviewOutcomeBox.SelectedIndex is not (1 or 2))
        {
            CoreStatusText.Text = "学习路径：请选择回答结果";
            return;
        }
        var correct = ReviewOutcomeBox.SelectedIndex == 1;
        var payload = JsonSerializer.Serialize(new
        {
            item_key = _activeLearningItem,
            client_event_id = $"desktop-{Guid.NewGuid():N}",
            correct,
            rating = correct ? 3 : 1,
            answer,
            rating_version = "desktop-v1",
            exposure_id = $"desktop-exposure-{Guid.NewGuid():N}",
        });
        try
        {
            using var response = await _supervisor.SendAsync(
                HttpMethod.Post,
                "/api/v1/learning/reviews",
                new StringContent(payload, Encoding.UTF8, "application/json"));
            CoreStatusText.Text = response.IsSuccessStatusCode
                ? "学习路径：复习已记录"
                : "学习路径：复习提交被拒绝";
            if (response.IsSuccessStatusCode)
            {
                LearningAnswerBox.Text = string.Empty;
                ReviewOutcomeBox.SelectedIndex = 0;
                SubmitReviewButton.IsEnabled = false;
            }
        }
        catch (Exception)
        {
            CoreStatusText.Text = "学习路径：复习提交中断";
        }
    }
}

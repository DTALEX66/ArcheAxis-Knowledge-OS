using System;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;

namespace ArcheAxis.Desktop;

public partial class MainWindow : Window
{
    private CoreSupervisor? _supervisor;

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
        var dbPath = Environment.GetEnvironmentVariable("ARCHAXIS_VNEXT_DB")
            ?? System.IO.Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "ArcheAxis", "vnext", "workspace.sqlite");
        CoreTextWorker? worker;
        try
        {
            worker = WorkerProfile.Load(AppContext.BaseDirectory,
                Environment.GetEnvironmentVariable("ARCHAXIS_WORKER_PROFILE"));
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
        }
        else
        {
            Title = $"ArcheAxis Learning Workspace (vNext) — core offline ({result.detail})";
            CoreStatusText.Text = "核心状态：离线";
        }
    }

    private void OnClosed(object? sender, EventArgs e)
    {
        // Supervisor shutdown: never leave an orphaned core process behind.
        _supervisor?.Dispose();
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
                if (response.IsSuccessStatusCode) imported++;
            }
        }
        catch (Exception)
        {
            CoreStatusText.Text = $"核心状态：导入中断，已提交 {imported}/{files.Count} 个资料";
            return;
        }
        CoreStatusText.Text = $"核心状态：已提交 {imported}/{files.Count} 个资料导入任务";
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
            CoreStatusText.Text = count == 0
                ? "学习路径：当前没有待复习项目"
                : $"学习路径：{count} 个项目可复习";
        }
        catch (Exception)
        {
            CoreStatusText.Text = "学习路径：队列读取中断";
        }
    }
}

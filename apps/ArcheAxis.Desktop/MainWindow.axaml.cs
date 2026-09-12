using System;
using Avalonia.Controls;
using Avalonia.Interactivity;

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
            return;
        }
        _supervisor = new CoreSupervisor(dbPath, textWorker: worker);
        var result = await _supervisor.StartAsync();
        if (result.ok)
        {
            Title = worker is null ? "星环知识平台 — 文本处理组件未配置"
                : "星环知识平台 — 已连接";
        }
        else
        {
            Title = $"ArcheAxis Learning Workspace (vNext) — core offline ({result.detail})";
        }
    }

    private void OnClosed(object? sender, EventArgs e)
    {
        // Supervisor shutdown: never leave an orphaned core process behind.
        _supervisor?.Dispose();
    }
}

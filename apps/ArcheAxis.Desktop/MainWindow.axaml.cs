using System;
using System.Net.Http;
using System.Text.Json;
using Avalonia.Controls;
using Avalonia.Interactivity;

namespace ArcheAxis.Desktop;

public partial class MainWindow : Window
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(5) };
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
        // Supervisor flow: if the core is not already answering on the default
        // port and a binary is configured (ARCHAXIS_CORE_BIN), spawn it and
        // handshake; otherwise probe the already-running core.
        var dbPath = Environment.GetEnvironmentVariable("ARCHAXIS_VNEXT_DB")
            ?? System.IO.Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "ArcheAxis", "vnext", "workspace.sqlite");
        _supervisor = new CoreSupervisor(dbPath);
        var result = await _supervisor.StartAsync();
        if (result.ok)
        {
            Title = $"ArcheAxis Learning Workspace (vNext) — {_supervisor.HandshakeRuntime} {_supervisor.HandshakeContract}";
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

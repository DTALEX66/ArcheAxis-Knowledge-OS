using System;
using System.Net.Http;
using System.Text.Json;
using Avalonia.Controls;
using Avalonia.Interactivity;

namespace ArcheAxis.Desktop;

public partial class MainWindow : Window
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(5) };
    private const string CoreVersionUrl = "http://127.0.0.1:47831/api/v1/system/version";

    public MainWindow()
    {
        InitializeComponent();
        Title = "ArcheAxis Learning Workspace (vNext) — core offline";
        Loaded += OnLoaded;
    }

    private async void OnLoaded(object? sender, RoutedEventArgs e)
    {
        // Supervisor handshake (minimal): ask the Rust Core for its identity.
        // The full Supervisor will spawn the core process; for the skeleton the
        // core is expected at the default local port (archeaxis-api server).
        try
        {
            var body = await Http.GetStringAsync(CoreVersionUrl);
            using var doc = JsonDocument.Parse(body);
            var runtime = doc.RootElement.GetProperty("runtime").GetString();
            var contract = doc.RootElement.GetProperty("contract").GetString();
            Title = $"ArcheAxis Learning Workspace (vNext) — {runtime} {contract}";
        }
        catch (Exception)
        {
            Title = "ArcheAxis Learning Workspace (vNext) — core offline";
        }
    }
}

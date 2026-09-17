using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace ArcheAxis.Desktop;

/// <summary>
/// Owns the optional DeepTutor web sidecar used by the formal Avalonia shell.
/// The sidecar never owns Core data or product truth; it only exposes a local
/// learning surface and is started from explicit, project-owned paths.
/// </summary>
public sealed class DeepTutorSupervisor : IDisposable
{
    private Process? _process;
    private readonly string _launcher;
    private readonly string _python;
    private readonly string _node;
    private readonly string _server;
    private readonly string _runtimeHome;
    private bool _disposed;

    public string Url { get; private set; } = "";
    public string Detail { get; private set; } = "未启动";

    private DeepTutorSupervisor(string launcher, string python, string node, string server, string runtimeHome)
    {
        _launcher = launcher;
        _python = python;
        _node = node;
        _server = server;
        _runtimeHome = runtimeHome;
    }

    public static DeepTutorSupervisor CreateFromEnvironment()
    {
        var launcher = Environment.GetEnvironmentVariable("ARCHEAXIS_DEEPTUTOR_LAUNCHER")
            ?? Path.Combine(AppContext.BaseDirectory, "scripts", "launch", "deeptutor_web.py");
        var python = Environment.GetEnvironmentVariable("ARCHEAXIS_DEEPTUTOR_PYTHON") ?? "";
        var node = Environment.GetEnvironmentVariable("ARCHEAXIS_NODE_PATH") ?? "";
        var server = Environment.GetEnvironmentVariable("ARCHEAXIS_DEEPTUTOR_SERVER") ?? "";
        var runtimeHome = Environment.GetEnvironmentVariable("ARCHEAXIS_DEEPTUTOR_RUNTIME_HOME")
            ?? Path.Combine(AppContext.BaseDirectory, "data", "deeptutor");
        return new DeepTutorSupervisor(launcher, python, node, server, runtimeHome);
    }

    public async Task<(bool ok, string detail)> StartAsync(CancellationToken cancellationToken = default)
    {
        if (_disposed) return (false, Detail = "学习工作台宿主已关闭");
        if (_process is { HasExited: false } && Url.Length > 0) return (true, Detail);
        if (!File.Exists(_launcher)) return (false, Detail = "未配置 DeepTutor wrapper");
        if (!File.Exists(_python)) return (false, Detail = "DeepTutor Python runtime 不可用");
        if (!File.Exists(_node)) return (false, Detail = "Node.js runtime 不可用");
        if (!File.Exists(_server)) return (false, Detail = "DeepTutor Web server 不可用");

        Directory.CreateDirectory(_runtimeHome);
        var backendPort = FreePort();
        var frontendPort = FreePort();
        var psi = new ProcessStartInfo
        {
            FileName = _python,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = false,
            RedirectStandardError = false,
            WorkingDirectory = _runtimeHome,
        };
        psi.ArgumentList.Add(_launcher);
        psi.ArgumentList.Add("--runtime-home");
        psi.ArgumentList.Add(_runtimeHome);
        psi.ArgumentList.Add("--python");
        psi.ArgumentList.Add(_python);
        psi.ArgumentList.Add("--node");
        psi.ArgumentList.Add(_node);
        psi.ArgumentList.Add("--server");
        psi.ArgumentList.Add(_server);
        psi.ArgumentList.Add("--backend-port");
        psi.ArgumentList.Add(backendPort.ToString());
        psi.ArgumentList.Add("--frontend-port");
        psi.ArgumentList.Add(frontendPort.ToString());
        try
        {
            _process = Process.Start(psi);
            if (_process is null) return (false, Detail = "DeepTutor 进程启动失败");
            var receipt = Path.Combine(_runtimeHome, "deeptutor-web-launch.json");
            var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(45);
            while (DateTime.UtcNow < deadline)
            {
                cancellationToken.ThrowIfCancellationRequested();
                if (_process.HasExited) return (false, Detail = "DeepTutor 在 READY 前退出");
                if (File.Exists(receipt))
                {
                    try
                    {
                        using var document = JsonDocument.Parse(await File.ReadAllTextAsync(receipt, cancellationToken));
                        var root = document.RootElement;
                        var status = root.TryGetProperty("status", out var statusValue) ? statusValue.GetString() : null;
                        var url = root.TryGetProperty("url", out var urlValue) ? urlValue.GetString() : null;
                        if (status == "READY" && IsLoopback(url))
                        {
                            Url = url!;
                            return (true, Detail = "DeepTutor 学习工作台已就绪");
                        }
                    }
                    catch (JsonException) { /* receipt is being replaced; retry */ }
                    catch (IOException) { /* receipt is being replaced; retry */ }
                }
                await Task.Delay(250, cancellationToken);
            }
            Stop();
            return (false, Detail = "DeepTutor 在 45 秒内未就绪");
        }
        catch (OperationCanceledException)
        {
            Stop();
            return (false, Detail = "DeepTutor 启动已取消");
        }
        catch (Exception ex)
        {
            Stop();
            return (false, Detail = $"DeepTutor 启动失败：{ex.GetType().Name}");
        }
    }

    public bool OpenBrowser()
    {
        if (!IsLoopback(Url)) return false;
        try
        {
            Process.Start(new ProcessStartInfo(Url) { UseShellExecute = true });
            return true;
        }
        catch (Exception) { return false; }
    }

    public void Stop()
    {
        var process = _process;
        _process = null;
        Url = "";
        if (process is null) return;
        try
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
                process.WaitForExit(5000);
            }
        }
        catch (Exception) { /* shutdown is best effort; never mask desktop close */ }
        finally { process.Dispose(); }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        Stop();
    }

    private static bool IsLoopback(string? value)
        => Uri.TryCreate(value, UriKind.Absolute, out var uri)
            && uri.Scheme == Uri.UriSchemeHttp
            && IPAddress.TryParse(uri.Host, out var address)
            && IPAddress.IsLoopback(address)
            && uri.UserInfo.Length == 0;

    private static int FreePort()
    {
        using var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        return ((IPEndPoint)listener.LocalEndpoint).Port;
    }
}

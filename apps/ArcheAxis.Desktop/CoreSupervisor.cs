using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace ArcheAxis.Desktop;

/// <summary>
/// Supervisor over the Rust Core process (v0.1 step 1: start core, handshake).
/// The core binary is resolved from ARCHAXIS_CORE_BIN, else a debug-build
/// default next to the repository. Start() spawns it, waits for the HTTP
/// readiness line, and performs the version handshake; Stop() terminates it.
/// </summary>
public sealed class CoreSupervisor : IDisposable
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(5) };
    private const string DefaultCoreUrl = "http://127.0.0.1:47831";

    private Process? _core;
    private readonly string _coreBin;
    private readonly string _dbPath;
    private bool _disposed;

    public string CoreUrl { get; private set; } = DefaultCoreUrl;
    public string? HandshakeRuntime { get; private set; }
    public string? HandshakeContract { get; private set; }

    public CoreSupervisor(string dbPath, string? coreBin = null)
    {
        _dbPath = dbPath;
        _coreBin = coreBin ?? Environment.GetEnvironmentVariable("ARCHAXIS_CORE_BIN")
            ?? Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "target", "debug", "archeaxis-api.exe");
    }

    public bool CoreAlreadyRunning()
    {
        try
        {
            using var resp = Http.GetAsync($"{DefaultCoreUrl}/api/v1/system/version").GetAwaiter().GetResult();
            return resp.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    public async Task<(bool ok, string detail)> StartAsync(CancellationToken ct = default)
    {
        if (CoreAlreadyRunning())
        {
            return await HandshakeAsync(DefaultCoreUrl, ct).ConfigureAwait(false);
        }
        if (!File.Exists(_coreBin))
        {
            return (false, $"core binary not found: {_coreBin} (set ARCHAXIS_CORE_BIN)");
        }
        var psi = new ProcessStartInfo
        {
            FileName = _coreBin,
            Arguments = $"\"{_dbPath}\"",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        _core = Process.Start(psi);
        if (_core is null)
        {
            return (false, "failed to start core process");
        }
        // wait for the readiness line on stdout
        var deadline = DateTime.UtcNow.AddSeconds(20);
        string? line = null;
        while (DateTime.UtcNow < deadline && _core.HasExited == false)
        {
            line = await _core.StandardOutput.ReadLineAsync(ct).ConfigureAwait(false);
            if (line is not null && line.Contains("ready on", StringComparison.Ordinal))
            {
                break;
            }
        }
        if (line is null || !line.Contains("ready on", StringComparison.Ordinal))
        {
            Stop();
            return (false, "core did not become ready in time");
        }
        // extract http://127.0.0.1:PORT (first whitespace token)
        var url = line.Substring(line.IndexOf("http://", StringComparison.Ordinal)).Split(' ')[0].Trim();
        return await HandshakeAsync(url, ct).ConfigureAwait(false);
    }

    private async Task<(bool ok, string detail)> HandshakeAsync(string url, CancellationToken ct)
    {
        try
        {
            var body = await Http.GetStringAsync($"{url}/api/v1/system/version", ct).ConfigureAwait(false);
            using var doc = JsonDocument.Parse(body);
            CoreUrl = url;
            HandshakeRuntime = doc.RootElement.GetProperty("runtime").GetString();
            HandshakeContract = doc.RootElement.GetProperty("contract").GetString();
            return (true, $"handshake ok: {HandshakeRuntime} {HandshakeContract}");
        }
        catch (Exception ex)
        {
            return (false, $"handshake failed: {ex.Message}");
        }
    }

    public void Stop()
    {
        if (_core is { HasExited: false })
        {
            try
            {
                _core.Kill(entireProcessTree: true);
            }
            catch
            {
                // already gone
            }
            _core.WaitForExit(5000);
        }
        _core?.Dispose();
        _core = null;
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }
        Stop();
        _disposed = true;
    }
}

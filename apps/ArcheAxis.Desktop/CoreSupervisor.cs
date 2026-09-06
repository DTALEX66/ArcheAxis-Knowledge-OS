using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace ArcheAxis.Desktop;

/// <summary>Owns one silent Core child; never adopts an unrelated loopback service.</summary>
public sealed class CoreSupervisor : IDisposable
{
    private static readonly HttpClient Http = new(new HttpClientHandler { UseProxy = false })
        { Timeout = TimeSpan.FromSeconds(5) };
    private Process? _core;
    private CancellationTokenSource? _startup;
    private readonly string _coreBin;
    private readonly string _dbPath;
    private bool _disposed;
    private int _starting;

    public string CoreUrl { get; private set; } = "";
    public string? HandshakeRuntime { get; private set; }
    public string? HandshakeContract { get; private set; }

    public CoreSupervisor(string dbPath, string? coreBin = null)
    {
        _dbPath = Path.GetFullPath(dbPath);
        _coreBin = coreBin ?? Environment.GetEnvironmentVariable("ARCHAXIS_CORE_BIN")
            ?? Path.Combine(AppContext.BaseDirectory, "archeaxis-api.exe");
    }

    public async Task<(bool ok, string detail)> StartAsync(CancellationToken ct = default)
    {
        if (_disposed) return (false, "supervisor is disposed");
        if (Interlocked.Exchange(ref _starting, 1) != 0) return (false, "startup already in progress");
        try
        {
            if (_core is { HasExited: false }) return (false, "owned core is already running");
            if (!File.Exists(_coreBin)) return (false, "core binary not found (set ARCHAXIS_CORE_BIN)");
            _startup = CancellationTokenSource.CreateLinkedTokenSource(ct);
            _startup.CancelAfter(TimeSpan.FromSeconds(20));
            var token = _startup.Token;
            var psi = new ProcessStartInfo
            {
                FileName = _coreBin,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };
            psi.ArgumentList.Add(_dbPath);
            psi.ArgumentList.Add("0"); // OS-assigned loopback port; no shared fixed-port attach.
            var process = Process.Start(psi);
            _core = process;
            if (process is null) return (false, "failed to start core process");
            _ = DrainAsync(process.StandardError);
            while (await process.StandardOutput.ReadLineAsync(token).ConfigureAwait(false) is { } line)
            {
                const string prefix = "archeaxis-api ready on ";
                if (!line.StartsWith(prefix, StringComparison.Ordinal)) continue;
                var address = line[prefix.Length..].Split(' ')[0];
                if (!Uri.TryCreate(address, UriKind.Absolute, out var uri)
                    || uri.Scheme != "http" || uri.Host != "127.0.0.1" || uri.Port <= 0
                    || uri.UserInfo.Length != 0 || uri.AbsolutePath != "/" || uri.Query.Length != 0)
                    throw new InvalidDataException("invalid Core readiness address");
                _ = DrainAsync(process.StandardOutput);
                var body = await Http.GetStringAsync(new Uri(uri, "/api/v1/system/version"), token).ConfigureAwait(false);
                using var doc = JsonDocument.Parse(body);
                var runtime = doc.RootElement.GetProperty("runtime").GetString();
                var contract = doc.RootElement.GetProperty("contract").GetString();
                if (runtime != "archeaxis-api" || contract != "0.1.0-outline")
                    throw new InvalidDataException("unsupported Core handshake");
                CoreUrl = uri.GetLeftPart(UriPartial.Authority);
                HandshakeRuntime = runtime;
                HandshakeContract = contract;
                return (true, $"owned core handshake ok: {runtime} {contract}");
            }
            Stop();
            return (false, "core exited before readiness");
        }
        catch (OperationCanceledException)
        {
            Stop();
            return (false, ct.IsCancellationRequested ? "startup cancelled" : "core readiness timed out");
        }
        catch (Exception ex)
        {
            Stop();
            return (false, $"core startup failed: {ex.GetType().Name}");
        }
        finally
        {
            _startup?.Dispose();
            _startup = null;
            Interlocked.Exchange(ref _starting, 0);
        }
    }

    private static async Task DrainAsync(StreamReader reader)
    {
        var buffer = new char[4096];
        try { while (await reader.ReadAsync(buffer).ConfigureAwait(false) > 0) { } }
        catch (IOException) { }
        catch (ObjectDisposedException) { }
    }

    public void Stop()
    {
        _startup?.Cancel();
        var process = _core;
        _core = null;
        CoreUrl = "";
        HandshakeRuntime = null;
        HandshakeContract = null;
        if (process is null) return;
        try
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
                if (!process.WaitForExit(5000)) throw new TimeoutException("owned Core did not exit");
            }
        }
        finally { process.Dispose(); }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        Stop();
    }
}

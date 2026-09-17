using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace ArcheAxis.Desktop;

public sealed record CoreTextWorker(string Python, string Script, string Staging);

/// <summary>Owns one silent Core child; never adopts an unrelated loopback service.</summary>
public sealed class CoreSupervisor : IDisposable
{
    private static readonly HttpClient Http = new(new HttpClientHandler { UseProxy = false, AllowAutoRedirect = false })
        { Timeout = TimeSpan.FromSeconds(5) };
    private Process? _core;
    private CancellationTokenSource? _startup;
    private readonly string _coreBin;
    private readonly string _dbPath;
    private readonly CoreTextWorker? _textWorker;
    private bool _disposed;
    private int _starting;
    private string? _launchToken;
    private string? _machineToken;
    private readonly object _lifecycle = new();

    public string CoreUrl { get; private set; } = "";
    public string? HandshakeRuntime { get; private set; }
    public string? HandshakeContract { get; private set; }

    public CoreSupervisor(string dbPath, string? coreBin = null, CoreTextWorker? textWorker = null)
    {
        _dbPath = Path.GetFullPath(dbPath);
        _textWorker = textWorker;
        _coreBin = coreBin ?? Environment.GetEnvironmentVariable("ARCHAXIS_CORE_BIN")
            ?? Path.Combine(AppContext.BaseDirectory, "archeaxis-api.exe");
    }

    public async Task<(bool ok, string detail)> StartAsync(CancellationToken ct = default)
    {
        CancellationToken token;
        lock (_lifecycle)
        {
            if (_disposed) return (false, "supervisor is disposed");
            if (_starting != 0) return (false, "startup already in progress");
            if (_core is { HasExited: false }) return (false, "owned core is already running");
            _core?.Dispose(); _core = null;
            _launchToken = null; _machineToken = null; CoreUrl = ""; HandshakeRuntime = null; HandshakeContract = null;
            _starting = 1;
            _startup = CancellationTokenSource.CreateLinkedTokenSource(ct);
            _startup.CancelAfter(TimeSpan.FromSeconds(20));
            token = _startup.Token;
        }
        try
        {
            if (!File.Exists(_coreBin)) return (false, "core binary not found (set ARCHAXIS_CORE_BIN)");
            var launchToken = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
            string machineToken;
            do { machineToken = Convert.ToHexString(RandomNumberGenerator.GetBytes(32)); }
            while (machineToken == launchToken);
            var sessionId = Convert.ToHexString(RandomNumberGenerator.GetBytes(16));
            var psi = new ProcessStartInfo
            {
                FileName = _coreBin,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                RedirectStandardInput = true,
                WorkingDirectory = Path.GetDirectoryName(Path.GetFullPath(_coreBin))!,
            };
            psi.ArgumentList.Add(_dbPath);
            psi.ArgumentList.Add("0"); // OS-assigned loopback port; no shared fixed-port attach.
            Process? process;
            lock (_lifecycle)
            {
                token.ThrowIfCancellationRequested();
                process = Process.Start(psi);
                _core = process;
            }
            if (process is null) return (false, "failed to start core process");
            _ = DrainAsync(process.StandardError);
            var worker = _textWorker is null ? null : new { python = _textWorker.Python, script = _textWorker.Script, staging = _textWorker.Staging };
            await process.StandardInput.WriteLineAsync(JsonSerializer.Serialize(new { protocol = "archeaxis.desktop-launch/v2", actor = "human", launch_token = launchToken, machine_token = machineToken, session_id = sessionId, text_worker = worker }).AsMemory(), token).ConfigureAwait(false);
            process.StandardInput.Close();
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
                using var request = new HttpRequestMessage(HttpMethod.Get, new Uri(uri, "/api/v1/system/version"));
                request.Headers.Add("x-archeaxis-launch-token", launchToken);
                using var response = await Http.SendAsync(request, token).ConfigureAwait(false);
                response.EnsureSuccessStatusCode();
                var body = await response.Content.ReadAsStringAsync(token).ConfigureAwait(false);
                using var doc = JsonDocument.Parse(body);
                var runtime = doc.RootElement.GetProperty("runtime").GetString();
                var contract = doc.RootElement.GetProperty("contract").GetString();
                if (runtime != "archeaxis-api" || contract != "0.1.0-outline")
                    throw new InvalidDataException("unsupported Core handshake");
                if (doc.RootElement.GetProperty("launch_protocol").GetString() != "archeaxis.desktop-launch/v2"
                    || doc.RootElement.GetProperty("actor").GetString() != "human")
                    throw new InvalidDataException("wrong Core human authority");
                if (doc.RootElement.GetProperty("session_id").GetString() != sessionId)
                    throw new InvalidDataException("wrong Core session");
                var actualDb = doc.RootElement.GetProperty("workspace_db").GetString();
                if (actualDb is null || !SameWorkspace(actualDb, _dbPath))
                    throw new InvalidDataException("wrong Core workspace");
                using var machineRequest = new HttpRequestMessage(HttpMethod.Get, new Uri(uri, "/api/v1/system/version"));
                machineRequest.Headers.Add("x-archeaxis-launch-token", machineToken);
                using var machineResponse = await Http.SendAsync(machineRequest, token).ConfigureAwait(false);
                machineResponse.EnsureSuccessStatusCode();
                using var machineDoc = JsonDocument.Parse(await machineResponse.Content.ReadAsStringAsync(token).ConfigureAwait(false));
                var machine = machineDoc.RootElement;
                if (machine.GetProperty("runtime").GetString() != runtime
                    || machine.GetProperty("contract").GetString() != contract
                    || machine.GetProperty("launch_protocol").GetString() != "archeaxis.desktop-launch/v2"
                    || machine.GetProperty("actor").GetString() != "machine"
                    || machine.GetProperty("session_id").GetString() != sessionId
                    || machine.GetProperty("workspace_db").GetString() is not { } machineDb
                    || !SameWorkspace(machineDb, _dbPath))
                    throw new InvalidDataException("wrong Core machine authority");
                lock (_lifecycle)
                {
                    token.ThrowIfCancellationRequested();
                    if (_disposed || !ReferenceEquals(_core, process) || process.HasExited)
                        throw new OperationCanceledException();
                    _launchToken = launchToken;
                    _machineToken = machineToken;
                    CoreUrl = uri.GetLeftPart(UriPartial.Authority);
                    HandshakeRuntime = runtime;
                    HandshakeContract = contract;
                    return (true, $"owned core handshake ok: {runtime} {contract}");
                }
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
            lock (_lifecycle)
            {
                _startup?.Dispose();
                _startup = null;
                _starting = 0;
            }
        }
    }

    private static bool SameWorkspace(string actual, string expected)
    {
        // SQLite reports the canonical extended Windows path held by Store.
        if (OperatingSystem.IsWindows() && actual.StartsWith(@"\\?\", StringComparison.Ordinal)) actual = actual[4..];
        return string.Equals(Path.GetFullPath(actual), expected,
            OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);
    }

    /// <summary>Authenticated requests stay on the verified owned Core origin.</summary>
    public Task<HttpResponseMessage> SendAsync(HttpMethod method, string path, HttpContent? content = null, CancellationToken ct = default)
        => SendAsAsync(false, method, path, content, ct);

    /// <summary>Project adapter requests use only machine authority; no credential is exposed.</summary>
    public Task<HttpResponseMessage> SendMachineAsync(HttpMethod method, string path, HttpContent? content = null, CancellationToken ct = default)
        => SendAsAsync(true, method, path, content, ct);

    private async Task<HttpResponseMessage> SendAsAsync(bool machine, HttpMethod method, string path, HttpContent? content, CancellationToken ct)
    {
        string launchToken, coreUrl;
        lock (_lifecycle)
        {
            var credential = machine ? _machineToken : _launchToken;
            if (_disposed || credential is null || CoreUrl.Length == 0) throw new InvalidOperationException("Core is not ready");
            launchToken = credential; coreUrl = CoreUrl;
        }
        if (!path.StartsWith("/api/v1/", StringComparison.Ordinal) || path.Contains('\\') || path.Contains('#'))
            throw new ArgumentException("Core API path required", nameof(path));
        var uri = new Uri(new Uri(coreUrl), path);
        if (uri.GetLeftPart(UriPartial.Authority) != coreUrl) throw new ArgumentException("Core origin mismatch", nameof(path));
        using var request = new HttpRequestMessage(method, uri) { Content = content };
        request.Headers.Add("x-archeaxis-launch-token", launchToken);
        var response = await Http.SendAsync(request, ct).ConfigureAwait(false);
        // Response diagnostics retain RequestMessage; strip the sent credential
        // before returning the response to either caller.
        response.RequestMessage?.Headers.Remove("x-archeaxis-launch-token");
        return response;
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
        Process? process;
        lock (_lifecycle)
        {
            _startup?.Cancel();
            process = _core;
            _core = null;
            CoreUrl = "";
            _launchToken = null;
            _machineToken = null;
            HandshakeRuntime = null;
            HandshakeContract = null;
        }
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
        lock (_lifecycle)
        {
            if (_disposed) return;
            _disposed = true;
        }
        Stop();
    }
}

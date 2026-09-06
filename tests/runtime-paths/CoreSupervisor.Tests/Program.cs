using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using ArcheAxis.Desktop;

if (args.Length > 0 && Path.GetFileName(args[0]).StartsWith("fixture-identity-")) {
    var fake = new TcpListener(IPAddress.Loopback, 0); fake.Start();
    Console.WriteLine($"archeaxis-api ready on http://127.0.0.1:{((IPEndPoint)fake.LocalEndpoint).Port}");
    using var client = await fake.AcceptTcpClientAsync();
    using var reader = new StreamReader(client.GetStream(), leaveOpen: true);
    while (await reader.ReadLineAsync() is { Length: > 0 }) { }
    if (Path.GetFileName(args[0]).Contains("redirect")) {
        await client.GetStream().WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:47831/stolen\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"));
    } else {
        using var bootstrap = JsonDocument.Parse(await Console.In.ReadToEndAsync());
        var session = Path.GetFileName(args[0]).Contains("workspace") || Path.GetFileName(args[0]).Contains("stop-race") ? bootstrap.RootElement.GetProperty("session_id").GetString() : "wrong-session";
        var workspace = Path.GetFileName(args[0]).Contains("workspace") ? args[0] + ".wrong" : args[0];
        var bytes = JsonSerializer.SerializeToUtf8Bytes(new { padding = Path.GetFileName(args[0]).Contains("stop-race") ? new string('x', 32 * 1024 * 1024) : "", runtime = "archeaxis-api", contract = "0.1.0-outline", session_id = session, workspace_db = workspace });
        await client.GetStream().WriteAsync(Encoding.ASCII.GetBytes($"HTTP/1.1 200 OK\r\nContent-Length: {bytes.Length}\r\nConnection: close\r\n\r\n"));
        await client.GetStream().WriteAsync(bytes);
        if (Path.GetFileName(args[0]).Contains("stop-race")) File.WriteAllText(args[0] + ".response-sent", "ready");
    }
    client.Close();
    await Task.Delay(Timeout.InfiniteTimeSpan);
    return 0;
}
if (args.Length > 0 && Path.GetFileName(args[0]).StartsWith("fixture-")) {
    // A child that fills stderr then never announces readiness must be bounded.
    await Console.Error.WriteAsync(new string('x', 200_000));
    await Task.Delay(Timeout.InfiniteTimeSpan);
    return 0;
}

// No test SDK, no UI. Real loopback service exercises the prior wrong-workspace
// attach bug without opening or touching any existing user service.
var listener = new TcpListener(IPAddress.Loopback, 47831);
try { listener.Start(); }
catch (SocketException) { Console.Error.WriteLine("BLOCKED: test port 47831 already owned; no process touched"); return 2; }
using var stop = new CancellationTokenSource();
var unrelatedRequests = 0;
var server = Task.Run(async () => {
    try {
        while (!stop.IsCancellationRequested) {
            using var client = await listener.AcceptTcpClientAsync(stop.Token);
            Interlocked.Increment(ref unrelatedRequests);
            using var reader = new StreamReader(client.GetStream(), leaveOpen: true);
            while (await reader.ReadLineAsync(stop.Token) is { Length: > 0 }) { }
            var bytes = Encoding.UTF8.GetBytes("{\"runtime\":\"archeaxis-rust-core\",\"contract\":\"archeaxis.vnext/v1\"}");
            await client.GetStream().WriteAsync(Encoding.ASCII.GetBytes($"HTTP/1.1 200 OK\r\nContent-Length: {bytes.Length}\r\nConnection: close\r\n\r\n"));
            await client.GetStream().WriteAsync(bytes);
        }
    } catch (OperationCanceledException) { }
});
try {
    var run = Environment.GetEnvironmentVariable("ARCHEAXIS_RUN_ROOT") ?? throw new Exception("project launcher required");
    using var supervisor = new CoreSupervisor(Path.Combine(run, "tmp", "own.sqlite"), Path.Combine(run, "absent-core.exe"));
    var result = await supervisor.StartAsync();
    if (result.ok) throw new Exception("Supervisor attached an unrelated same-port service instead of requested workspace");
    Console.WriteLine("PASS: unrelated same-port service was not adopted");
    using var hung = new CoreSupervisor(Path.Combine(run, "tmp", "fixture-no-ready.sqlite"), Environment.ProcessPath);
    using var deadline = new CancellationTokenSource(TimeSpan.FromMilliseconds(600));
    var timer = System.Diagnostics.Stopwatch.StartNew();
    var cancelled = await hung.StartAsync(deadline.Token);
    if (cancelled.ok || timer.Elapsed > TimeSpan.FromSeconds(4)) throw new Exception("readiness cancellation did not bound a stderr-flooding child");
    Console.WriteLine("PASS: cancelled stderr-flooding child returned failure within deadline");
    var racePath = Path.Combine(run, "tmp", "fixture-identity-stop-race.sqlite");
    using (var race = new CoreSupervisor(racePath, Environment.ProcessPath)) {
        using var bounded = new CancellationTokenSource(TimeSpan.FromSeconds(8));
        var startup = race.StartAsync(bounded.Token);
        while (!File.Exists(racePath + ".response-sent") && !startup.IsCompleted) await Task.Delay(1);
        await Task.Delay(20);
        if (startup.IsCompleted) {
            race.Stop();
            Console.WriteLine("SKIP: startup completed before stop-race observation window");
        } else {
            race.Stop();
            if ((await startup).ok || race.CoreUrl.Length != 0) throw new Exception("stopped startup republished ready state");
            Console.WriteLine("PASS: Stop during handshake parsing cannot republish readiness");
        }
    }
    foreach (var scenario in new[] { "session", "workspace", "redirect" }) {
        using var fake = new CoreSupervisor(Path.Combine(run, "tmp", $"fixture-identity-{scenario}.sqlite"), Environment.ProcessPath);
        using var bounded = new CancellationTokenSource(TimeSpan.FromSeconds(4));
        if ((await fake.StartAsync(bounded.Token)).ok) throw new Exception($"accepted false Core identity: {scenario}");
        if (unrelatedRequests != 0) throw new Exception("redirect reached an unrelated credential recipient");
    }
    Console.WriteLine("PASS: wrong-session 200 and credential-redirect handshake rejected");
    var core = Environment.GetEnvironmentVariable("ARCHAXIS_CORE_BIN") ?? throw new Exception("real Core binary required");
    var db = Path.Combine(run, "tmp", "core with spaces.sqlite");
    var workerProfile = new CoreTextWorker(Environment.GetEnvironmentVariable("ARCHEAXIS_PYTHON") ?? throw new Exception("project Python required"),
        Path.GetFullPath("services/python-workers/transport/text_ndjson.py"), Path.Combine(run, "tmp", "worker-staging"));
    using var real = new CoreSupervisor(db, core, workerProfile);
    var started = await real.StartAsync();
    if (!started.ok || !File.Exists(db) || new Uri(real.CoreUrl).Port is 0 or 47831)
        throw new Exception($"real owned Core failed: {started.detail}");
    var ownedUrl = real.CoreUrl;
    using (var imported = await real.SendAsync(HttpMethod.Post, "/api/v1/imports", new StringContent("{\"name\":\"desktop.txt\",\"content_base64\":\"aGVsbG8=\"}", Encoding.UTF8, "application/json"))) {
        if (imported.StatusCode != HttpStatusCode.Accepted) throw new Exception("desktop import failed");
        using var source = JsonDocument.Parse(await imported.Content.ReadAsStringAsync());
        var enqueue = JsonSerializer.Serialize(new { job_id = "desktop-job", kind = "text", input_ref = source.RootElement.GetProperty("source_id").GetString() });
        using var queued = await real.SendAsync(HttpMethod.Post, "/api/v1/jobs", new StringContent(enqueue, Encoding.UTF8, "application/json"));
        if (queued.StatusCode != HttpStatusCode.Accepted) throw new Exception("desktop enqueue failed");
    }
    var executionBody = new StringContent("{\"deadline_ms\":5000}", Encoding.UTF8, "application/json");
    executionBody.Headers.Add("idempotency-key", "desktop-attempt");
    using (var execution = await real.SendAsync(HttpMethod.Post, "/api/v1/jobs/desktop-job/executions", executionBody)) {
        if (execution.StatusCode != HttpStatusCode.Accepted) throw new Exception("desktop could not execute the actual worker");
    }
    using (var bounded = new CancellationTokenSource(TimeSpan.FromSeconds(6))) {
        while (true) {
            using var read = await real.SendAsync(HttpMethod.Get, "/api/v1/jobs/desktop-job", ct: bounded.Token);
            using var status = JsonDocument.Parse(await read.Content.ReadAsStringAsync(bounded.Token));
            var state = status.RootElement.GetProperty("state").GetString();
            if (state == "succeeded") break;
            if (state != "running") throw new Exception("desktop execution did not succeed");
            await Task.Delay(10, bounded.Token);
        }
        using var output = await real.SendAsync(HttpMethod.Get, "/api/v1/jobs/desktop-job/outputs/text", ct: bounded.Token);
        using var converted = JsonDocument.Parse(await output.Content.ReadAsStringAsync(bounded.Token));
        if (converted.RootElement.GetProperty("content").GetString() != "hello") throw new Exception("desktop worker output differs");
    }
    Console.WriteLine("PASS: silent C# -> authenticated Core -> actual Python -> persisted output");
    using (var readback = await real.SendAsync(HttpMethod.Get, "/api/v1/workspaces/info")) {
        if (!readback.IsSuccessStatusCode) throw new Exception("owned authenticated readback failed");
    }
    using var unauthenticated = new HttpClient(new HttpClientHandler { UseProxy = false });
    if ((await unauthenticated.GetAsync(ownedUrl + "/api/v1/workspaces/info")).StatusCode != HttpStatusCode.Unauthorized)
        throw new Exception("production Core was reachable without launch credential");
    string sessionBefore;
    using (var identity = await real.SendAsync(HttpMethod.Get, "/api/v1/system/version")) {
        using var body = JsonDocument.Parse(await identity.Content.ReadAsStringAsync());
        sessionBefore = body.RootElement.GetProperty("session_id").GetString()!;
    }
    foreach (var foreign in new[] { "https://example.invalid/api/v1/test", "//127.0.0.1:47831/stolen", "/api/v1/\\\\127.0.0.1/stolen" }) {
        try { using var rejected = await real.SendAsync(HttpMethod.Get, foreign); throw new Exception("accepted non-Core destination"); }
        catch (ArgumentException) { }
    }
    real.Stop();
    using var http = new HttpClient(new HttpClientHandler { UseProxy = false }) { Timeout = TimeSpan.FromSeconds(5) };
    try { await http.GetAsync(ownedUrl); throw new Exception("owned Core survived Stop"); }
    catch (HttpRequestException) { }
    using var other = new CoreSupervisor(Path.Combine(run, "tmp", "second workspace.sqlite"), core);
    var pair = await Task.WhenAll(real.StartAsync(), other.StartAsync());
    if (pair.Any(p => !p.ok) || real.CoreUrl == other.CoreUrl) throw new Exception("independent concurrent launches failed");
    using (var current = await real.SendAsync(HttpMethod.Get, "/api/v1/system/version"))
    using (var independent = await other.SendAsync(HttpMethod.Get, "/api/v1/system/version")) {
        using var firstBody = JsonDocument.Parse(await current.Content.ReadAsStringAsync());
        using var secondBody = JsonDocument.Parse(await independent.Content.ReadAsStringAsync());
        var sessionAfter = firstBody.RootElement.GetProperty("session_id").GetString();
        if (sessionAfter == sessionBefore || sessionAfter == secondBody.RootElement.GetProperty("session_id").GetString())
            throw new Exception("restarted or concurrent Core reused another launch identity");
    }
    real.Stop(); other.Stop();
    if (OperatingSystem.IsWindows()) {
        var shortBuffer = new StringBuilder(32768);
        var length = NativePaths.GetShortPathName(db, shortBuffer, (uint)shortBuffer.Capacity);
        if (length > 0 && length < shortBuffer.Capacity && !string.Equals(db, shortBuffer.ToString(), StringComparison.OrdinalIgnoreCase)) {
            using var shortName = new CoreSupervisor(shortBuffer.ToString(), core);
            var shortStarted = await shortName.StartAsync();
            if (!shortStarted.ok) throw new Exception("same workspace via native 8.3 name was rejected");
            shortName.Stop();
            Console.WriteLine("PASS: actual Windows short-path workspace identity");
        } else Console.WriteLine("SKIP: filesystem supplied no distinct 8.3 name");
    }
    if (unrelatedRequests != 0) throw new Exception("credential escaped to unrelated service");
    Console.WriteLine("PASS: real Core with spaced path, assigned port, handshake and shutdown");
    return 0;
} finally { stop.Cancel(); listener.Stop(); await server; }

internal static class NativePaths {
    [System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
    internal static extern uint GetShortPathName(string path, StringBuilder buffer, uint length);
}

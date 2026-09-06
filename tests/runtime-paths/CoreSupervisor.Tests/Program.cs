using System.Net;
using System.Net.Sockets;
using System.Text;
using ArcheAxis.Desktop;

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
var server = Task.Run(async () => {
    try {
        while (!stop.IsCancellationRequested) {
            using var client = await listener.AcceptTcpClientAsync(stop.Token);
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
    var core = Environment.GetEnvironmentVariable("ARCHAXIS_CORE_BIN") ?? throw new Exception("real Core binary required");
    var db = Path.Combine(run, "tmp", "core with spaces.sqlite");
    using var real = new CoreSupervisor(db, core);
    var started = await real.StartAsync();
    if (!started.ok || !File.Exists(db) || new Uri(real.CoreUrl).Port is 0 or 47831)
        throw new Exception($"real owned Core failed: {started.detail}");
    var ownedUrl = real.CoreUrl;
    real.Stop();
    using var http = new HttpClient(new HttpClientHandler { UseProxy = false }) { Timeout = TimeSpan.FromSeconds(5) };
    try { await http.GetAsync(ownedUrl); throw new Exception("owned Core survived Stop"); }
    catch (HttpRequestException) { }
    Console.WriteLine("PASS: real Core with spaced path, assigned port, handshake and shutdown");
    return 0;
} finally { stop.Cancel(); listener.Stop(); await server; }

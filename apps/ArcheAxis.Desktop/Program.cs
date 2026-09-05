using Avalonia;
using System;

namespace ArcheAxis.Desktop;

class Program
{
    // Initialization code. Don't use any Avalonia, third-party APIs or any
    // SynchronizationContext-reliant code before AppMain is called: things aren't initialized
    // yet and stuff might break.
    [STAThread]
    public static int Main(string[] args)
    {
        // Headless supervisor smoke (CI-safe): ArcheAxis.Desktop.exe --smoke [dbPath]
        // spawns the Rust core, completes the handshake, then shuts it down.
        // No Avalonia UI is created in this mode.
        if (args.Length > 0 && args[0] == "--smoke")
        {
            return RunSupervisorSmoke(args.Length > 1 ? args[1] : null);
        }
        BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
        return 0;
    }

    private static int RunSupervisorSmoke(string? dbPath)
    {
        dbPath ??= System.IO.Path.Combine(
            System.IO.Path.GetTempPath(), "archeaxis-vnext-smoke.sqlite");
        try
        {
            using var supervisor = new CoreSupervisor(dbPath);
            var result = supervisor.StartAsync().GetAwaiter().GetResult();
            Console.WriteLine(result.ok ? $"SMOKE OK: {result.detail}" : $"SMOKE FAIL: {result.detail}");
            supervisor.Stop();
            return result.ok ? 0 : 1;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"SMOKE ERROR: {ex.Message}");
            return 1;
        }
    }

    // Avalonia configuration, don't remove; also used by visual designer.
    public static AppBuilder BuildAvaloniaApp()
        => AppBuilder.Configure<App>()
            .UsePlatformDetect()
#if DEBUG
            .WithDeveloperTools()
#endif
            .WithInterFont()
            .LogToTrace();
}

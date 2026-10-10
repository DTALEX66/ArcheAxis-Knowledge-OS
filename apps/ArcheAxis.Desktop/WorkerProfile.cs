using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace ArcheAxis.Desktop;

/// <summary>Public runtime paths only; never discover interpreters or inspect agent configuration.</summary>
public static class WorkerProfile
{
    private static readonly HashSet<string> PrivateNames = new(StringComparer.OrdinalIgnoreCase)
    {
        ".git", ".codex", ".dsh", ".zcode", ".hermes", ".openhuman", ".claude",
        ".agents", ".agent", ".cursor", ".continue", ".aider", ".gemini", ".opencode",
        ".openhands", ".cline", ".roo", ".kilocode", ".windsurf", ".copilot",
        ".ssh", ".aws", ".azure", ".gnupg", "agent-private", "private-agent-state",
        "sessions", "memories", "keychain", "credentials", "auth", "browser-data",
        ".npmrc", ".pypirc", ".netrc"
    };
    public static CoreTextWorker? Load(string applicationDirectory, string? explicitPath = null)
    {
        var path = Resolve(applicationDirectory, explicitPath ?? "worker-profile.json");
        if (!File.Exists(path))
        {
            if (explicitPath is null) return null;
            throw new InvalidDataException("configured worker profile is missing");
        }
        if (new FileInfo(path).Length > 16384) throw new InvalidDataException("worker profile exceeds limit");
        try
        {
            using var document = JsonDocument.Parse(File.ReadAllText(path));
            if (document.RootElement.ValueKind != JsonValueKind.Object)
                throw new InvalidDataException("worker profile must be an object");
            var fields = new Dictionary<string, string>(StringComparer.Ordinal);
            var routeEntries = new List<(string Capability, string Script)>();
            foreach (var field in document.RootElement.EnumerateObject())
            {
                // `routes` is read here rather than refused. The staged runtime's reader accepted it in
                // `deb2238a` because a launch that cannot declare capability routes registers none,
                // and this reader had the same refusal. A profile carrying routes used to throw
                // "unknown ... worker profile field", which the window reports as an invalid worker
                // configuration and refuses to start on.
                if (field.Name == "routes")
                {
                    if (field.Value.ValueKind != JsonValueKind.Array)
                        throw new InvalidDataException("worker profile routes must be an array");
                    foreach (var entry in field.Value.EnumerateArray())
                    {
                        if (entry.ValueKind != JsonValueKind.Object)
                            throw new InvalidDataException("worker profile route must be an object");
                        string? capability = null;
                        // Named `routeScript` rather than `script`: the enclosing method declares a
                        // local `script` for the text worker, and C# refuses the shadowing (CS0136).
                        string? routeScript = null;
                        foreach (var part in entry.EnumerateObject())
                        {
                            // A route names a capability and the script that serves it. Anything else
                            // is refused by name rather than dropped: a dropped route would surface
                            // later as an unexplained capability that is simply missing.
                            if (part.Name == "capability" && part.Value.ValueKind == JsonValueKind.String)
                                capability = part.Value.GetString();
                            else if (part.Name == "script" && part.Value.ValueKind == JsonValueKind.String)
                                routeScript = part.Value.GetString();
                            else
                                throw new InvalidDataException("unknown or invalid worker profile route field");
                        }
                        if (string.IsNullOrWhiteSpace(capability) || string.IsNullOrWhiteSpace(routeScript))
                            throw new InvalidDataException("worker profile route needs a capability and a script");
                        routeEntries.Add((capability, routeScript));
                    }
                    continue;
                }
                if (field.Name is not ("schema" or "python" or "script" or "staging")
                    || field.Value.ValueKind != JsonValueKind.String
                    || !fields.TryAdd(field.Name, field.Value.GetString()!))
                    throw new InvalidDataException("unknown, duplicate or invalid worker profile field");
            }
            if (fields.Count != 4 || fields.GetValueOrDefault("schema") != "archeaxis.worker-profile/v1")
                throw new InvalidDataException("unsupported or incomplete worker profile");
            var directory = Path.GetDirectoryName(path)!;
            var python = Resolve(directory, fields["python"]);
            var script = Resolve(directory, fields["script"]);
            var staging = Resolve(directory, fields["staging"]);
            if (!File.Exists(python) || !File.Exists(script))
                throw new InvalidDataException("worker interpreter or script is missing");
            // Every declared route script is resolved and checked the same way the text script is, and
            // is required to exist: a route whose worker is absent would register a capability that
            // fails at job time.
            var routes = new List<CoreWorkerRoute>(routeEntries.Count);
            foreach (var declared in routeEntries)
            {
                var resolved = Resolve(directory, declared.Script);
                if (!File.Exists(resolved))
                    throw new InvalidDataException($"worker route script is missing: {declared.Capability}");
                routes.Add(new CoreWorkerRoute(declared.Capability, resolved));
            }
            return new CoreTextWorker(python, script, staging, routes);
        }
        catch (JsonException) { throw new InvalidDataException("invalid worker profile JSON"); }
    }

    private static string Resolve(string directory, string value)
    {
        if (string.IsNullOrWhiteSpace(value)) throw new InvalidDataException("empty worker profile path");
        var spelling = value.Replace('\\', '/');
        if (spelling.StartsWith("E:", StringComparison.OrdinalIgnoreCase) || spelling.StartsWith("//", StringComparison.Ordinal)
            || Array.Exists(spelling.Split('/'), part => part == ".."))
            throw new InvalidDataException("unsafe worker profile path");
        var full = Path.GetFullPath(value, Path.GetFullPath(directory));
        var components = full.Replace('\\', '/').Split('/');
        if (full.StartsWith("E:", StringComparison.OrdinalIgnoreCase)
            || full.StartsWith("\\\\", StringComparison.Ordinal)
            || Array.Exists(components, part => part.StartsWith(".env", StringComparison.OrdinalIgnoreCase)
                || PrivateNames.Contains(part))
            || full.Replace('\\', '/').Contains("/.project-local/agents/", StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("protected worker profile path");
        var ancestors = new List<string>();
        for (var current = full; current is not null; current = Path.GetDirectoryName(current))
            ancestors.Add(current);
        ancestors.Reverse();
        foreach (var current in ancestors)
        {
            try
            {
                if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidDataException("linked worker profile path");
            }
            catch (FileNotFoundException) { }
            catch (DirectoryNotFoundException) { }
        }
        return full;
    }
}

using Avalonia;
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

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
        // Headless synthetic first-use journey (CI-safe):
        // ArcheAxis.Desktop.exe --learning-smoke [dbPath]
        // exercises assessment, learner observation, FSRS projection and cold
        // Core restart readback. It never claims learner input is Knowledge truth.
        if (args.Length > 0 && args[0] == "--learning-smoke")
        {
            return RunLearningSmoke(args.Length > 1 ? args[1] : null);
        }
        BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
        return 0;
    }

    private static int RunSupervisorSmoke(string? dbPath)
    {
        // Smoke is an explicit project-run operation.  Never fall back to the
        // process/user TEMP directory, which creates an unmanaged second store.
        if (string.IsNullOrWhiteSpace(dbPath))
        {
            Console.Error.WriteLine("SMOKE ERROR: provide an explicit project-local database path");
            return 2;
        }
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

    private static int RunLearningSmoke(string? dbPath)
        => RunLearningSmokeAsync(dbPath).GetAwaiter().GetResult();

    private static async Task<int> RunLearningSmokeAsync(string? dbPath)
    {
        var runSuffix = Guid.NewGuid().ToString("N");
        var itemKey = $"p3-headless-learning-card-{runSuffix}";
        var answer = $"Synthetic learner observation {runSuffix}: FSRS uses prior review state.";
        var eventKey = $"p3-headless-learning-review-{runSuffix}";
        const string reviewNow = "2026-09-02T00:00:00+00:00";
        if (string.IsNullOrWhiteSpace(dbPath))
        {
            Console.Error.WriteLine("LEARNING SMOKE ERROR: provide an explicit project-local database path");
            return 2;
        }

        try
        {
            string assessmentId;
            string knowledgeVersion;
            using (var supervisor = new CoreSupervisor(dbPath))
            {
                var started = await supervisor.StartAsync().ConfigureAwait(false);
                if (!started.ok) throw new InvalidOperationException(started.detail);

                using var knowledge = await PostJsonAsync(supervisor, "/api/v1/knowledge-items", new
                {
                    knowledge_type = "PERSONAL_DEFINITION",
                    body = $"Synthetic personal learning note {runSuffix}: FSRS uses prior review state.",
                    status = "accepted",
                    created_by = "owner",
                }).ConfigureAwait(false);
                var knowledgeId = RequiredString(knowledge.RootElement, "knowledge_id");

                await PostJsonAsync(supervisor,
                    $"/api/v1/learning/items/{Uri.EscapeDataString(itemKey)}/references",
                    new { knowledge_id = knowledgeId }).ConfigureAwait(false);
                using var assessment = await PostJsonAsync(supervisor,
                    $"/api/v1/learning/items/{Uri.EscapeDataString(itemKey)}/assessment",
                    new { knowledge_id = knowledgeId }).ConfigureAwait(false);
                assessmentId = RequiredString(assessment.RootElement, "assessment_id");
                knowledgeVersion = RequiredString(assessment.RootElement, "knowledge_version");
                if (RequiredString(assessment.RootElement, "knowledge_id") != knowledgeId
                    || RequiredString(assessment.RootElement, "item_key") != itemKey)
                    throw new InvalidOperationException("assessment is not bound to the synthetic item and Knowledge");

                using var review = await PostJsonAsync(supervisor, "/api/v1/learning/reviews", new
                {
                    item_key = itemKey,
                    client_event_id = eventKey,
                    correct = false,
                    rating = 1,
                    now = reviewNow,
                    answer,
                    assessment_id = assessmentId,
                    knowledge_version = knowledgeVersion,
                }).ConfigureAwait(false);
                ValidateReviewProjection(review.RootElement, answer);
            }

            using (var reopened = new CoreSupervisor(dbPath))
            {
                var started = await reopened.StartAsync().ConfigureAwait(false);
                if (!started.ok) throw new InvalidOperationException(started.detail);

                using var assessment = await GetJsonAsync(reopened,
                    $"/api/v1/learning/items/{Uri.EscapeDataString(itemKey)}/assessment").ConfigureAwait(false);
                if (RequiredString(assessment.RootElement, "assessment_id") != assessmentId
                    || RequiredString(assessment.RootElement, "knowledge_version") != knowledgeVersion)
                    throw new InvalidOperationException("assessment readback changed across Core restart");

                using var history = await GetJsonAsync(reopened,
                    $"/api/v1/learning/events/{Uri.EscapeDataString(itemKey)}").ConfigureAwait(false);
                if (!history.RootElement.TryGetProperty("events", out var events)
                    || events.ValueKind != JsonValueKind.Array || events.GetArrayLength() == 0)
                    throw new InvalidOperationException("learning event readback is empty");
                var latest = events[events.GetArrayLength() - 1];
                using var outcome = JsonDocument.Parse(RequiredString(latest, "outcome"));
                if (RequiredString(outcome.RootElement, "answer") != answer)
                    throw new InvalidOperationException("learner answer readback changed across Core restart");
                ValidateScheduleAndProjection(outcome.RootElement);
            }

            Console.WriteLine($"LEARNING SMOKE OK: item={itemKey}; assessment={assessmentId}; answer_saved=true; fsrs=true; mastery_projection_closed=false");
            return 0;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"LEARNING SMOKE ERROR: {ex.Message}");
            return 1;
        }
    }

    private static async Task<JsonDocument> PostJsonAsync(CoreSupervisor supervisor, string path, object payload)
    {
        using var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        using var response = await supervisor.SendAsync(HttpMethod.Post, path, content).ConfigureAwait(false);
        return await ReadJsonResponseAsync(response, path).ConfigureAwait(false);
    }

    private static async Task<JsonDocument> GetJsonAsync(CoreSupervisor supervisor, string path)
    {
        using var response = await supervisor.SendAsync(HttpMethod.Get, path).ConfigureAwait(false);
        return await ReadJsonResponseAsync(response, path).ConfigureAwait(false);
    }

    private static async Task<JsonDocument> ReadJsonResponseAsync(HttpResponseMessage response, string path)
    {
        var body = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"{path} returned {(int)response.StatusCode}: {body}");
        return JsonDocument.Parse(body);
    }

    private static string RequiredString(JsonElement root, string name)
    {
        if (root.TryGetProperty(name, out var value)
            && value.ValueKind == JsonValueKind.String
            && !string.IsNullOrWhiteSpace(value.GetString()))
            return value.GetString()!;
        throw new InvalidOperationException($"response is missing non-empty string '{name}'");
    }

    private static void ValidateReviewProjection(JsonElement review, string expectedAnswer)
    {
        if (RequiredString(review, "answer") != expectedAnswer
            || RequiredString(review, "schedule_authority") != "fsrs")
            throw new InvalidOperationException("review did not preserve the learner answer and FSRS authority");
        ValidateProjection(review.GetProperty("mastery_projection"));
    }

    private static void ValidateScheduleAndProjection(JsonElement outcome)
    {
        if (RequiredString(outcome.GetProperty("schedule"), "authority") != "fsrs")
            throw new InvalidOperationException("readback did not retain FSRS schedule authority");
        ValidateProjection(outcome.GetProperty("mastery_projection"));
    }

    private static void ValidateProjection(JsonElement projection)
    {
        if (RequiredString(projection, "status") != "projection"
            || !projection.TryGetProperty("closed", out var closed)
            || closed.ValueKind != JsonValueKind.False)
            throw new InvalidOperationException("mastery projection was closed or presented as Truth");
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

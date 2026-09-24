using System;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace ArcheAxis.Desktop;

public sealed record CoreTextOutputReadResult(
    string State,
    bool IsReady,
    string? Content,
    string? MetadataJson,
    string? Error);

/// <summary>Reads verified text output through the owned Core runtime; never reads or writes its database directly.</summary>
public static class CoreTextOutputReader
{
    public static async Task<CoreTextOutputReadResult> ReadAsync(
        CoreSupervisor core,
        string sourceId,
        string jobId,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(sourceId) || string.IsNullOrWhiteSpace(jobId))
            return new CoreTextOutputReadResult("invalid_reference", false, null, null, "source_id/job_id missing");

        using var statusResponse = await core.SendAsync(
            HttpMethod.Get,
            $"/api/v1/jobs/{Uri.EscapeDataString(jobId)}",
            ct: cancellationToken).ConfigureAwait(false);
        if (!statusResponse.IsSuccessStatusCode)
            return new CoreTextOutputReadResult("status_unavailable", false, null, null, $"HTTP {(int)statusResponse.StatusCode}");

        using var statusDocument = JsonDocument.Parse(await statusResponse.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false));
        var statusRoot = statusDocument.RootElement;
        var returnedJobId = statusRoot.TryGetProperty("job_id", out var jobValue) ? jobValue.GetString() : null;
        var state = statusRoot.TryGetProperty("state", out var stateValue) ? stateValue.GetString() ?? "unknown" : "unknown";
        if (!string.Equals(returnedJobId, jobId, System.StringComparison.Ordinal))
            return new CoreTextOutputReadResult("identity_mismatch", false, null, null, "Core returned a different job_id");
        var inputRef = statusRoot.TryGetProperty("input_ref", out var inputRefValue) ? inputRefValue.GetString() : null;
        if (!string.Equals(inputRef, sourceId, StringComparison.Ordinal))
            return new CoreTextOutputReadResult("source_mismatch", false, null, null, "Core job is not bound to the requested source_id");
        if (!string.Equals(state, "succeeded", System.StringComparison.Ordinal))
            return new CoreTextOutputReadResult(state ?? "unknown", false, null, null, null);

        using var outputResponse = await core.SendAsync(
            HttpMethod.Get,
            $"/api/v1/jobs/{Uri.EscapeDataString(jobId)}/outputs/text",
            ct: cancellationToken).ConfigureAwait(false);
        if (!outputResponse.IsSuccessStatusCode)
            return new CoreTextOutputReadResult(state, false, null, null, $"output HTTP {(int)outputResponse.StatusCode}");

        using var outputDocument = JsonDocument.Parse(await outputResponse.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false));
        var outputRoot = outputDocument.RootElement;
        var content = outputRoot.TryGetProperty("content", out var contentValue)
            && contentValue.ValueKind == JsonValueKind.String
            ? contentValue.GetString()
            : null;
        var metadata = outputRoot.TryGetProperty("metadata", out var metadataValue)
            ? metadataValue.GetRawText()
            : null;
        if (content is null)
            return new CoreTextOutputReadResult(state, false, null, metadata, "Core text output did not contain string content");

        return new CoreTextOutputReadResult(state, true, content, metadata, null);
    }
}

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
    long? TransformId,
    string? RawSha256,
    string? MetadataJson,
    string? Error)
{
    public bool IsPermissionDenied => Error?.Contains("HTTP 401", StringComparison.Ordinal) == true
        || Error?.Contains("HTTP 403", StringComparison.Ordinal) == true;
}

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
            return new CoreTextOutputReadResult("invalid_reference", false, null, null, null, null, "source_id/job_id missing");

        using var statusResponse = await core.SendAsync(
            HttpMethod.Get,
            $"/api/v1/jobs/{Uri.EscapeDataString(jobId)}",
            ct: cancellationToken).ConfigureAwait(false);
        if (!statusResponse.IsSuccessStatusCode)
            return new CoreTextOutputReadResult("status_unavailable", false, null, null, null, null, $"HTTP {(int)statusResponse.StatusCode}");

        using var statusDocument = JsonDocument.Parse(await statusResponse.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false));
        var statusRoot = statusDocument.RootElement;
        var returnedJobId = statusRoot.TryGetProperty("job_id", out var jobValue) ? jobValue.GetString() : null;
        var state = statusRoot.TryGetProperty("state", out var stateValue) ? stateValue.GetString() ?? "unknown" : "unknown";
        if (!string.Equals(returnedJobId, jobId, System.StringComparison.Ordinal))
            return new CoreTextOutputReadResult("identity_mismatch", false, null, null, null, null, "Core returned a different job_id");
        var inputRef = statusRoot.TryGetProperty("input_ref", out var inputRefValue) ? inputRefValue.GetString() : null;
        if (!string.Equals(inputRef, sourceId, StringComparison.Ordinal))
            return new CoreTextOutputReadResult("source_mismatch", false, null, null, null, null, "Core job is not bound to the requested source_id");
        if (!string.Equals(state, "succeeded", System.StringComparison.Ordinal))
            return new CoreTextOutputReadResult(state ?? "unknown", false, null, null, null, null, null);

        using var outputResponse = await core.SendAsync(
            HttpMethod.Get,
            $"/api/v1/sources/{Uri.EscapeDataString(sourceId)}/jobs/{Uri.EscapeDataString(jobId)}/transform",
            ct: cancellationToken).ConfigureAwait(false);
        if (!outputResponse.IsSuccessStatusCode)
            return new CoreTextOutputReadResult(state, false, null, null, null, null, $"transform HTTP {(int)outputResponse.StatusCode}");

        using var outputDocument = JsonDocument.Parse(await outputResponse.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false));
        var outputRoot = outputDocument.RootElement;
        var content = outputRoot.TryGetProperty("content", out var contentValue)
            && contentValue.ValueKind == JsonValueKind.String
            ? contentValue.GetString()
            : null;
        var metadata = outputRoot.TryGetProperty("metadata", out var metadataValue)
            ? metadataValue.GetRawText()
            : null;
        var returnedSourceId = outputRoot.TryGetProperty("source_id", out var sourceValue) ? sourceValue.GetString() : null;
        var returnedOutputJobId = outputRoot.TryGetProperty("job_id", out var outputJobValue) ? outputJobValue.GetString() : null;
        var transformId = outputRoot.TryGetProperty("transform_id", out var transformValue) && transformValue.TryGetInt64(out var parsedTransformId)
            ? parsedTransformId
            : (long?)null;
        var rawSha256 = outputRoot.TryGetProperty("raw_sha256", out var shaValue) ? shaValue.GetString() : null;
        if (!string.Equals(returnedSourceId, sourceId, StringComparison.Ordinal)
            || !string.Equals(returnedOutputJobId, jobId, StringComparison.Ordinal)
            || transformId is null
            || string.IsNullOrWhiteSpace(rawSha256))
            return new CoreTextOutputReadResult(state, false, null, null, null, metadata, "Core transform identity is incomplete or mismatched");
        if (content is null)
            return new CoreTextOutputReadResult(state, false, null, null, null, metadata, "Core text output did not contain string content");

        return new CoreTextOutputReadResult(state, true, content, transformId, rawSha256, metadata, null);
    }
}

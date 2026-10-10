using System;
using System.Text.Json;

namespace ArcheAxis.Desktop;

/// <summary>Restore an observation only into the Assessment that received it.</summary>
public static class LearningAnswerReadback
{
    public static string? AnswerForAssessment(JsonElement outcome, string? activeAssessmentId)
    {
        if (string.IsNullOrWhiteSpace(activeAssessmentId)
            || outcome.ValueKind != JsonValueKind.Object
            || !outcome.TryGetProperty("assessment_id", out var assessmentId)
            || assessmentId.ValueKind != JsonValueKind.String
            || !string.Equals(assessmentId.GetString(), activeAssessmentId, StringComparison.Ordinal)
            || !outcome.TryGetProperty("answer", out var answer)
            || answer.ValueKind != JsonValueKind.String)
            return null;

        var text = answer.GetString();
        return string.IsNullOrWhiteSpace(text) ? null : text;
    }
}

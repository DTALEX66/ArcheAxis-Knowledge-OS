using System;
using System.Text.Json;

namespace ArcheAxis.Desktop;

/// <summary>Persisted Core identities, never a client-generated evaluation or score.</summary>
public sealed class MachineLearningJourney
{
    public string? AnswerId { get; private set; }
    public string? KnowledgeId { get; private set; }
    public string? Question { get; private set; }
    public string? AnswerText { get; private set; }
    public string? FailedTaskId { get; private set; }
    public string? CorrectionId { get; private set; }
    public string? CorrectedAnswer { get; private set; }
    public string? ErrorNote { get; private set; }
    public bool CorrectionAccepted { get; private set; }
    public string? RetestId { get; private set; }
    public string? RetestText { get; private set; }
    public string HistoryText { get; private set; } = "";
    public bool CanRecordCorrection => AnswerId is not null && (CorrectionId is null || RetestId is not null);
    public string? LastTaskId => RetestId ?? FailedTaskId ?? AnswerId;

    public static string Required(JsonElement value, string key)
    {
        if (value.ValueKind == JsonValueKind.Object
            && value.TryGetProperty(key, out var field)
            && field.ValueKind == JsonValueKind.String
            && !string.IsNullOrWhiteSpace(field.GetString()))
            return field.GetString()!;
        throw new InvalidOperationException($"回执缺少 {key}");
    }

    public void CaptureAnswer(JsonElement value, string knowledgeId, string question)
    {
        if (Required(value, "schema") != "archeaxis.machine-answer/v1"
            || Required(value, "knowledge_id") != knowledgeId
            || Required(value, "question") != question)
            throw new InvalidOperationException("回答回执与当前问题不匹配");
        var id = Required(value, "answer_id");
        var answer = Required(value.GetProperty("answer"), "answer");
        AnswerId = id; KnowledgeId = knowledgeId; Question = question; AnswerText = answer;
        FailedTaskId = null; CorrectionId = null; CorrectedAnswer = null; ErrorNote = null;
        CorrectionAccepted = false; RetestId = null; RetestText = null;
    }

    public object CorrectionRequest(string correctedAnswer, string errorNote)
    {
        if (AnswerId is null || string.IsNullOrWhiteSpace(correctedAnswer) || string.IsNullOrWhiteSpace(errorNote))
            throw new InvalidOperationException("请先读取回答，再填写你的纠正和具体错误");
        return new { answer_id = RetestId ?? AnswerId, knowledge_id = RetestId is null ? KnowledgeId : CorrectionId, question = Question,
            machine_answer = RetestText ?? AnswerText, corrected_answer = correctedAnswer, error_note = errorNote, reviewer = "human" };
    }

    public void CaptureCorrection(JsonElement value, string correctedAnswer, string errorNote)
    {
        var answerId = RetestId ?? AnswerId;
        var knowledgeId = RetestId is null ? KnowledgeId : CorrectionId;
        var answerText = RetestText ?? AnswerText;
        if (answerId is null || Required(value, "schema") != "archeaxis.machine-correction/v1"
            || Required(value, "answer_id") != answerId
            || Required(value, "corrects_knowledge_id") != knowledgeId
            || Required(value, "question") != Question
            || Required(value, "machine_answer") != answerText
            || Required(value, "corrected_answer") != correctedAnswer
            || Required(value, "error_note") != errorNote)
            throw new InvalidOperationException("纠正回执与原始回答不匹配");
        var candidate = Required(value, "correction_candidate_id");
        var failed = Required(value, "failed_task_id");
        if (RetestId is not null)
        {
            HistoryText += $"先前问题：{Question}\n先前回答：{AnswerText}\n你的纠正：{CorrectedAnswer}\n重测回答：{RetestText}\n\n";
            AnswerId = answerId; KnowledgeId = knowledgeId; AnswerText = answerText;
        }
        CorrectionId = candidate; FailedTaskId = failed; CorrectedAnswer = correctedAnswer; ErrorNote = errorNote;
        CorrectionAccepted = false; RetestId = null; RetestText = null;
    }

    public void MarkCorrectionAccepted(JsonElement knowledge, JsonElement qualification)
    {
        CorrectionAccepted = false;
        if (CorrectionId is null || Required(knowledge, "knowledge_id") != CorrectionId
            || Required(qualification, "knowledge_id") != CorrectionId
            || Required(knowledge, "status") != "accepted"
            || !qualification.TryGetProperty("active", out var active) || active.ValueKind != JsonValueKind.True)
            throw new InvalidOperationException("纠正尚未读回为已接受的当前知识");
        CorrectionAccepted = true;
    }

    public void ClearCorrectionAcceptance() => CorrectionAccepted = false;

    public object RetestRequest()
    {
        if (!CorrectionAccepted || CorrectionId is null || FailedTaskId is null)
            throw new InvalidOperationException("请先亲自接受纠正，再重测原题");
        return new { retest_of = FailedTaskId, knowledge_id = CorrectionId, question = Question,
            max_tokens = 512, timeout_s = 120 };
    }

    public void CaptureRetest(JsonElement value)
    {
        if (Required(value, "schema") != "archeaxis.machine-retest/v1"
            || Required(value, "retest_of") != FailedTaskId
            || Required(value, "knowledge_id") != CorrectionId
            || Required(value, "question") != Question)
            throw new InvalidOperationException("重测回执未绑定原题和失败任务");
        var id = Required(value, "retest_task_id");
        var answer = Required(value.GetProperty("answer"), "answer");
        RetestId = id; RetestText = answer;
    }

    public static MachineLearningJourney FromTask(JsonElement task)
    {
        var id = Required(task, "task_id");
        var scope = Required(task, "scope");
        using var stored = JsonDocument.Parse(Required(task, "conditions"));
        var doc = stored.RootElement;
        var result = new MachineLearningJourney();
        result.ReadStoredRound(doc, 0);
        var expected = scope switch {
            "runtime.answer" => result.AnswerId,
            "runtime.evaluation.failed" => result.FailedTaskId,
            "runtime.retest" => result.RetestId,
            _ => throw new InvalidOperationException("这条收据不属于机器问答旅程")
        };
        if (id != expected) throw new InvalidOperationException("任务身份与持久化内容不一致");
        return result;
    }

    private void ReadStoredRound(JsonElement doc, int depth)
    {
        if (depth > 24) throw new InvalidOperationException("历史轮次超过本次可读取范围");
        var schema = Required(doc, "schema");
        if (schema == "archeaxis.machine-answer/v1")
            CaptureAnswer(doc, Required(doc, "knowledge_id"), Required(doc, "question"));
        else if (schema == "archeaxis.machine-retest/v1")
        {
            ReadStoredRound(doc.GetProperty("prior").GetProperty("conditions"), depth + 1);
            CaptureRetest(doc);
        }
        else throw new InvalidOperationException("未识别的机器回答记录");
        // Failed evaluation of a retest preserves that retest and its prior round.
        if (doc.TryGetProperty("correction", out var correction))
            CaptureCorrection(correction, Required(correction, "corrected_answer"), Required(correction, "error_note"));
    }
}

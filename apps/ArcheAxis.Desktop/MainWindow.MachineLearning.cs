using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Interactivity;

namespace ArcheAxis.Desktop;

public partial class MainWindow
{
    private MachineLearningJourney _machineJourney = new();
    private bool _machineJourneyInProgress;

    private void OnUseKnowledgeForMachineClick(object? sender, RoutedEventArgs e)
    {
        if (_machineJourneyInProgress) return;
        var id = _learningEligibleKnowledgeId;
        if (string.IsNullOrWhiteSpace(id) || id != KnowledgeIdBox.Text?.Trim())
        {
            ShowToast("请先读取一条已接受的知识。", "error");
            return;
        }
        MachineKnowledgeIdBox.Text = id;
        MachineKnowledgePreviewText.Text = "已选择知识；提问时会重新核验知识状态。";
        SetSection("machine-growth", "机器学习");
        MachineQuestionBox.Focus();
    }

    private void UpdateMachineJourneyControls()
    {
        var idle = !_machineJourneyInProgress && !_machineTaskLoadInProgress;
        MachineAskButton.IsEnabled = idle;
        MachineQuestionBox.IsEnabled = idle;
        MachineKnowledgeIdBox.IsEnabled = idle;
        MachineTaskLoadButton.IsEnabled = idle;
        MachineTaskIdBox.IsEnabled = idle;
        MachineErrorNoteBox.IsEnabled = idle && _machineJourney.CanRecordCorrection;
        MachineCorrectedAnswerBox.IsEnabled = MachineErrorNoteBox.IsEnabled;
        MachineCorrectButton.IsEnabled = MachineErrorNoteBox.IsEnabled;
        MachineAcceptCorrectionButton.IsEnabled = idle && _machineJourney.CorrectionId is not null && !_machineJourney.CorrectionAccepted;
        MachineRetestButton.IsEnabled = idle && _machineJourney.CorrectionAccepted;
        MachineJourneyReadbackButton.IsEnabled = idle && _machineJourney.LastTaskId is not null;
        MachineJourneyProgress.IsIndeterminate = !_reducedMotion;
        MachineJourneyProgress.IsVisible = _machineJourneyInProgress && !_reducedMotion;
        MachineJourneyWaitingText.IsVisible = _machineJourneyInProgress && _reducedMotion;
    }

    private sealed class MachineJourneyHttpException : Exception
    {
        public int Status { get; }
        public MachineJourneyHttpException(int status, string detail) : base(detail) => Status = status;
    }

    private async Task<JsonElement> MachineCoreCallAsync(HttpMethod method, string path, object? payload = null)
    {
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
            throw new InvalidOperationException("Core 尚未连接");
        using var content = payload is null ? null
            : new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        // Human correction and acceptance use the verified human launch identity.
        using var response = await _supervisor.SendAsync(method, path, content);
        var text = await response.Content.ReadAsStringAsync();
        MachineJourneyDiagnosticsText.Text = $"{method} {path}\nHTTP {(int)response.StatusCode}\n{text[..Math.Min(text.Length, 6000)]}";
        if (!response.IsSuccessStatusCode)
            throw new MachineJourneyHttpException((int)response.StatusCode, text);
        using var json = JsonDocument.Parse(text);
        return json.RootElement.Clone();
    }

    private async Task RunMachineJourneyAsync(string loading, Func<Task> action)
    {
        if (_machineJourneyInProgress || _machineTaskLoadInProgress) return;
        _machineJourneyInProgress = true;
        UpdateMachineJourneyControls();
        SetStatus(MachineJourneyStatusText, loading, "loading");
        try { await action(); }
        catch (MachineJourneyHttpException error)
        {
            SetStatus(MachineJourneyStatusText, error.Status switch {
                401 or 403 => "当前会话没有执行此操作的权限，请重新连接。",
                404 => "所选知识或已保存记录不可用，请检查选择后重试。",
                409 => "记录与当前操作不一致，请先重新读取，再决定下一步。",
                503 => "模型暂不可用，请检查本地模型是否就绪。",
                _ => "操作未完成，请展开更多信息查看原因。"
            }, error.Status is 401 or 403 ? "permission" : "error");
        }
        catch (TaskCanceledException)
        {
            SetStatus(MachineJourneyStatusText, "等待超时；操作可能已经保存。请先读取记录，避免重复提交。", "error");
        }
        catch (Exception error)
        {
            MachineJourneyDiagnosticsText.Text = error.Message;
            SetStatus(MachineJourneyStatusText, "没有取得匹配的已保存记录，请展开更多信息检查并重新读取。", "error");
        }
        finally { _machineJourneyInProgress = false; UpdateMachineJourneyControls(); }
    }

    private void RenderMachineJourney()
    {
        MachineAnswerText.Text = _machineJourney.AnswerText ?? "回答会显示在这里，请对照知识自行判断。";
        MachineAskedQuestionText.Text = _machineJourney.Question ?? "先选择知识，再提出一个具体问题。";
        MachineCorrectionPreviewText.Text = _machineJourney.CorrectedAnswer is null
            ? "发现错误后，写下原因和你认为正确的回答。"
            : $"你的纠正：{_machineJourney.CorrectedAnswer}\n原因：{_machineJourney.ErrorNote}\n" +
                (_machineJourney.CorrectionAccepted ? "纠正已作为知识保存，可以重测原题。" : "纠正已保存为候选；请复核内容后亲自接受。");
        MachineRetestAnswerText.Text = _machineJourney.RetestText ?? "接受纠正后，再次回答同一个问题。";
        MachineJourneyHistoryText.Text = _machineJourney.HistoryText.Length == 0 ? "尚无更早轮次。" : _machineJourney.HistoryText;
        MachineJourneyIdentityText.Text = $"answer_id={_machineJourney.AnswerId ?? "—"}\n" +
            $"failed_task_id={_machineJourney.FailedTaskId ?? "—"}\ncorrection_candidate_id={_machineJourney.CorrectionId ?? "—"}\n" +
            $"retest_task_id={_machineJourney.RetestId ?? "—"}\nknowledge_id={_machineJourney.KnowledgeId ?? "—"}";
        MachineTaskIdBox.Text = _machineJourney.LastTaskId;
        UpdateMachineJourneyControls();
    }

    private async Task VerifyMachineCorrectionAsync(MachineLearningJourney journey)
    {
        if (journey.CorrectionId is null) return;
        journey.ClearCorrectionAcceptance();
        var path = $"/api/v1/knowledge-items/{Uri.EscapeDataString(journey.CorrectionId)}";
        var knowledge = await MachineCoreCallAsync(HttpMethod.Get, $"{path}/v3");
        var qualification = await MachineCoreCallAsync(HttpMethod.Get, $"{path}/qualification");
        if (MachineLearningJourney.Required(knowledge, "status") == "accepted")
            journey.MarkCorrectionAccepted(knowledge, qualification);
    }

    private async Task ReadMachineJourneyAsync(string taskId)
    {
        var task = await MachineCoreCallAsync(HttpMethod.Get, $"/api/v1/machine/tasks/{Uri.EscapeDataString(taskId)}");
        if (MachineLearningJourney.Required(task, "task_id") != taskId)
            throw new InvalidOperationException("读回任务身份不一致");
        var restored = MachineLearningJourney.FromTask(task);
        await VerifyMachineCorrectionAsync(restored);
        _machineJourney = restored;
        RenderMachineJourney();
    }

    private async void OnMachineAnswerClick(object? sender, RoutedEventArgs e)
    {
        var knowledgeId = MachineKnowledgeIdBox.Text?.Trim() ?? "";
        var question = MachineQuestionBox.Text?.Trim() ?? "";
        if (knowledgeId.Length == 0 || question.Length == 0)
        {
            SetStatus(MachineJourneyStatusText, "请从知识库选择一条已接受的知识，并填写问题。", "empty");
            return;
        }
        await RunMachineJourneyAsync("正在对照所选知识回答…", async () => {
            var path = $"/api/v1/knowledge-items/{Uri.EscapeDataString(knowledgeId)}";
            var knowledge = await MachineCoreCallAsync(HttpMethod.Get, $"{path}/v3");
            var qualification = await MachineCoreCallAsync(HttpMethod.Get, $"{path}/qualification");
            if (MachineLearningJourney.Required(knowledge, "knowledge_id") != knowledgeId
                || MachineLearningJourney.Required(knowledge, "status") != "accepted"
                || MachineLearningJourney.Required(qualification, "knowledge_id") != knowledgeId
                || !qualification.TryGetProperty("active", out var active) || active.ValueKind != JsonValueKind.True)
                throw new InvalidOperationException("请选择已接受、未被替代的知识");
            MachineKnowledgePreviewText.Text = MachineLearningJourney.Required(knowledge, "body");
            var answer = await MachineCoreCallAsync(HttpMethod.Post, "/api/v1/machine/answers",
                new { knowledge_id = knowledgeId, question, max_tokens = 512, timeout_s = 120 });
            var next = new MachineLearningJourney();
            next.CaptureAnswer(answer, knowledgeId, question);
            _machineJourney = next;
            MachineErrorNoteBox.Text = ""; MachineCorrectedAnswerBox.Text = "";
            RenderMachineJourney();
            await ReadMachineJourneyAsync(next.AnswerId!);
            SetStatus(MachineJourneyStatusText, "回答已保存并重新读取。请判断内容是否正确。", "success");
        });
    }

    private async void OnMachineCorrectionClick(object? sender, RoutedEventArgs e)
    {
        var corrected = MachineCorrectedAnswerBox.Text?.Trim() ?? "";
        var error = MachineErrorNoteBox.Text?.Trim() ?? "";
        if (corrected.Length == 0 || error.Length == 0)
        {
            SetStatus(MachineJourneyStatusText, "请填写具体错误及你认为正确的回答。", "empty");
            return;
        }
        await RunMachineJourneyAsync("正在保存你的纠正…", async () => {
            var correction = await MachineCoreCallAsync(HttpMethod.Post, "/api/v1/machine/corrections",
                _machineJourney.CorrectionRequest(corrected, error));
            _machineJourney.CaptureCorrection(correction, corrected, error);
            RenderMachineJourney();
            await ReadMachineJourneyAsync(_machineJourney.FailedTaskId!);
            SetStatus(MachineJourneyStatusText, "纠正候选已保存并重新读取；请复核后亲自接受。", "success");
        });
    }

    private async void OnMachineAcceptCorrectionClick(object? sender, RoutedEventArgs e)
    {
        var id = _machineJourney.CorrectionId;
        if (id is null) return;
        await RunMachineJourneyAsync("正在保存你对纠正的接受决定…", async () => {
            var reviewed = await MachineCoreCallAsync(HttpMethod.Post,
                $"/api/v1/knowledge-items/{Uri.EscapeDataString(id)}/review-decisions",
                new { action = "accepted", reviewer = "human", note = "Human accepted the displayed correction in Desktop." });
            if (MachineLearningJourney.Required(reviewed, "knowledge_id") != id)
                throw new InvalidOperationException("接受回执身份不一致");
            await VerifyMachineCorrectionAsync(_machineJourney);
            if (!_machineJourney.CorrectionAccepted) throw new InvalidOperationException("接受状态尚未读回");
            RenderMachineJourney();
            SetStatus(MachineJourneyStatusText, "你的接受决定已保存并核验，可以重测原题。", "success");
        });
    }

    private async void OnMachineRetestClick(object? sender, RoutedEventArgs e)
    {
        await RunMachineJourneyAsync("正在使用已接受的纠正重新回答原题…", async () => {
            await VerifyMachineCorrectionAsync(_machineJourney);
            var retest = await MachineCoreCallAsync(HttpMethod.Post, "/api/v1/machine/retests", _machineJourney.RetestRequest());
            _machineJourney.CaptureRetest(retest);
            MachineErrorNoteBox.Text = ""; MachineCorrectedAnswerBox.Text = "";
            RenderMachineJourney();
            await ReadMachineJourneyAsync(_machineJourney.RetestId!);
            SetStatus(MachineJourneyStatusText, "重测回答已保存并读回；请比较两次回答。未判定重测正确。", "success");
        });
    }

    private async void OnMachineJourneyReadbackClick(object? sender, RoutedEventArgs e)
    {
        var taskId = _machineJourney.LastTaskId ?? MachineTaskIdBox.Text?.Trim();
        if (string.IsNullOrWhiteSpace(taskId)) return;
        await RunMachineJourneyAsync("正在重新读取已保存的回答和纠正…", async () => {
            await ReadMachineJourneyAsync(taskId);
            SetStatus(MachineJourneyStatusText, "已重新读取保存的旅程记录；请继续你的判断。", "success");
        });
    }
}

using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Interactivity;

namespace ArcheAxis.Desktop;

public partial class MainWindow
{
    private CourseLessonReadback? _courseLesson;
    private bool _courseInProgress;
    private int _courseRequestVersion;

    private async Task EnrollKnowledgeAsync(string knowledgeId, string itemKey, Func<bool> current, string? expectedVersion = null)
    {
        if (_supervisor is null || !current()) throw new OperationCanceledException("页面已变化，请重新选择后开始学习。");
        using var reference = await _supervisor.SendAsync(HttpMethod.Post,
            $"/api/v1/learning/items/{Uri.EscapeDataString(itemKey)}/references",
            new StringContent(JsonSerializer.Serialize(new { knowledge_id = knowledgeId }), Encoding.UTF8, "application/json"));
        if (!reference.IsSuccessStatusCode)
            throw new InvalidOperationException(IsPermissionStatus(reference.StatusCode)
                ? "没有保存学习来源的权限，请检查当前会话。" : "学习来源未保存，请确认知识仍然有效后重试。");
        if (!current()) throw new OperationCanceledException("学习来源已保存；页面已切换，可回到学习队列查看或重试。");
        using var assessment = await _supervisor.SendAsync(HttpMethod.Post,
            $"/api/v1/learning/items/{Uri.EscapeDataString(itemKey)}/assessment",
            new StringContent(JsonSerializer.Serialize(new { knowledge_id = knowledgeId }), Encoding.UTF8, "application/json"));
        if (!assessment.IsSuccessStatusCode)
            throw new InvalidOperationException(IsPermissionStatus(assessment.StatusCode)
                ? "学习来源已保存，但没有生成学习题目的权限。" : "学习来源已保存，但学习题目尚未生成；请重试。已有记录会保留。");
        using var document = JsonDocument.Parse(await assessment.Content.ReadAsStringAsync());
        CourseLessonReadback.ValidateAssessment(document.RootElement, itemKey, knowledgeId, expectedVersion);
    }

    private async Task<JsonDocument> CourseRequestAsync(HttpMethod method, string path, object? body = null)
    {
        if (_supervisor is null) throw new InvalidOperationException("服务尚未连接。");
        using var content = body is null ? null : new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
        using var response = await _supervisor.SendAsync(method, path, content);
        var raw = await response.Content.ReadAsStringAsync();
        CourseDiagnosticsText.Text += $"\n{path}\nHTTP {(int)response.StatusCode}\n{raw}";
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException(IsPermissionStatus(response.StatusCode) ? "没有操作课件的权限，请检查当前会话。"
                : response.StatusCode == System.Net.HttpStatusCode.Conflict ? "知识或资料来源已变化，请重新读取后生成课件。"
                : response.StatusCode == System.Net.HttpStatusCode.NotFound ? "未找到这条知识或课件，请重新选择。"
                : response.StatusCode == System.Net.HttpStatusCode.UnprocessableEntity ? "这条知识暂不符合课件生成要求。"
                : "课件服务暂不可用或返回内容无法核验，请重试。");
        return JsonDocument.Parse(raw);
    }

    private void ShowCourseLesson(CourseLessonReadback lesson)
    {
        _courseLesson = lesson;
        CourseTitleText.Text = lesson.Title;
        CourseSourceText.Text = $"来源：{ResolveSourceTitle(lesson.SourceId)}";
        CourseLessonText.Text = lesson.LessonText;
        CourseLessonBody.IsVisible = true;
        CourseStartLearningButton.IsEnabled = lesson.ItemKey.Length > 0;
        CourseIdReadbackBox.Text = lesson.CourseId;
        SetStatus(CourseStatusText, "课件候选已读回，仍待你复核。开始学习只会建立学习题目，不会接受课件或改变知识结论。", "warning");
    }

    private async void OnGenerateCourseClick(object? sender, RoutedEventArgs e)
    {
        if (_courseInProgress || _addKnowledgeToLearningInProgress) return;
        var knowledgeId = _learningEligibleKnowledgeId;
        if (string.IsNullOrWhiteSpace(knowledgeId) || knowledgeId != KnowledgeIdBox.Text?.Trim()
            || _supervisor is null || _supervisor.CoreUrl.Length == 0)
        { SetStatus(KnowledgeLearningStatusText, "请先选择有效且已确认的知识，再生成课件。", "error"); return; }
        var knowledgeVersion = _knowledgeRequestVersion;
        var request = ++_courseRequestVersion;
        bool Current() => request == _courseRequestVersion && knowledgeVersion == _knowledgeRequestVersion
            && _learningEligibleKnowledgeId == knowledgeId && _activeSection == "knowledge";
        _courseInProgress = true;
        CourseDiagnosticsText.Text = "";
        GenerateCourseButton.IsEnabled = false;
        CourseStartLearningButton.IsEnabled = false;
        _courseLesson = null;
        CourseLessonBody.IsVisible = false;
        SetStatus(KnowledgeLearningStatusText, "正在生成课件候选并读取正文…", "loading");
        try
        {
            using var created = await CourseRequestAsync(HttpMethod.Post, "/api/v1/courses/from-knowledge", new { knowledge_id = knowledgeId });
            if (!Current()) return;
            var lesson = CourseLessonReadback.Generated(created.RootElement, knowledgeId);
            using var stored = await CourseRequestAsync(HttpMethod.Get, $"/api/v1/courses/{Uri.EscapeDataString(lesson.CourseId)}");
            if (!Current()) return;
            lesson = lesson.ReadStored(stored.RootElement);
            using var rendered = await CourseRequestAsync(HttpMethod.Post, $"/api/v1/courses/{Uri.EscapeDataString(lesson.CourseId)}/render", new { artifact_id = lesson.ArtifactId });
            if (!Current()) return;
            lesson = lesson.ReadRendered(rendered.RootElement);
            ShowCourseLesson(lesson);
            SetStatus(KnowledgeLearningStatusText, "课件候选已保存，正在打开课件供你审阅。", "success");
            SetSection("learning", "学习");
        }
        catch (Exception error)
        { if (Current()) SetStatus(KnowledgeLearningStatusText, UserDisplay.Failure(error.Message), "error"); }
        finally { _courseInProgress = false; GenerateCourseButton.IsEnabled = _knowledgeReadStatus == "accepted"
            && !string.IsNullOrWhiteSpace(_learningEligibleKnowledgeId) && OpenKnowledgeSourceButton.IsEnabled; }
    }

    private async void OnReadCourseClick(object? sender, RoutedEventArgs e)
    {
        if (_courseInProgress || _addKnowledgeToLearningInProgress) return;
        var id = CourseIdReadbackBox.Text?.Trim() ?? "";
        if (id.Length == 0 || id.Length > 256) { SetStatus(CourseStatusText, "请填写要读取的课件标识。", "empty"); return; }
        var request = ++_courseRequestVersion;
        bool Current() => request == _courseRequestVersion && _activeSection == "learning" && CourseIdReadbackBox.Text?.Trim() == id;
        _courseInProgress = true; CourseReadbackButton.IsEnabled = false; CourseStartLearningButton.IsEnabled = false;
        CourseDiagnosticsText.Text = "";
        _courseLesson = null; CourseLessonBody.IsVisible = false;
        SetStatus(CourseStatusText, "正在读取已保存课件…", "loading");
        try
        {
            using var stored = await CourseRequestAsync(HttpMethod.Get, $"/api/v1/courses/{Uri.EscapeDataString(id)}");
            if (!Current()) return;
            var artifact = stored.RootElement.GetProperty("manifest").GetProperty("artifacts")[0];
            var lesson = CourseLessonReadback.Stored(stored.RootElement, id, MachineLearningJourney.Required(artifact, "artifact_id"));
            // Obtain Core's persisted learning suggestion, also rechecking the canonical source.
            using var suggestion = await CourseRequestAsync(HttpMethod.Post, "/api/v1/courses/from-knowledge", new { knowledge_id = lesson.KnowledgeId });
            if (!Current()) return;
            var confirmed = CourseLessonReadback.Generated(suggestion.RootElement, lesson.KnowledgeId);
            if (confirmed.CourseId != id || confirmed.ArtifactId != lesson.ArtifactId)
                throw new InvalidOperationException("这条课件不属于当前知识生成的学习路径，请在知识页重新选择。");
            lesson = confirmed.ReadStored(stored.RootElement);
            using var rendered = await CourseRequestAsync(HttpMethod.Post, $"/api/v1/courses/{Uri.EscapeDataString(id)}/render", new { artifact_id = lesson.ArtifactId });
            if (!Current()) return;
            ShowCourseLesson(lesson.ReadRendered(rendered.RootElement));
        }
        catch (Exception error) { if (Current()) SetStatus(CourseStatusText, UserDisplay.Failure(error.Message), "error"); }
        finally { _courseInProgress = false; CourseReadbackButton.IsEnabled = true; }
    }

    private async void OnStartCourseLearningClick(object? sender, RoutedEventArgs e)
    {
        if (_courseInProgress || _addKnowledgeToLearningInProgress || _courseLesson is not { LessonText.Length: > 0, ItemKey.Length: > 0 } lesson) return;
        var request = _courseRequestVersion;
        bool Current() => request == _courseRequestVersion && ReferenceEquals(lesson, _courseLesson) && _activeSection == "learning";
        _addKnowledgeToLearningInProgress = true; CourseStartLearningButton.IsEnabled = false;
        SetStatus(CourseStatusText, "正在核验课件来源并建立学习题目…", "loading");
        try
        {
            using var stored = await CourseRequestAsync(HttpMethod.Get, $"/api/v1/courses/{Uri.EscapeDataString(lesson.CourseId)}");
            lesson.ReadStored(stored.RootElement);
            if (!Current()) return;
            await EnrollKnowledgeAsync(lesson.KnowledgeId, lesson.ItemKey, Current, lesson.KnowledgeVersion);
            if (!Current()) return;
            _selectedLearningItemKey = lesson.ItemKey;
            SetStatus(CourseStatusText, "学习题目已保存。课件仍为待复核候选，请作答后自行评价。", "success");
            OnLearningClick(sender, e);
        }
        catch (Exception error) { if (Current()) SetStatus(CourseStatusText, UserDisplay.Failure(error.Message), "error"); }
        finally { _addKnowledgeToLearningInProgress = false; CourseStartLearningButton.IsEnabled = _courseLesson is { LessonText.Length: > 0, ItemKey.Length: > 0 }; }
    }
}

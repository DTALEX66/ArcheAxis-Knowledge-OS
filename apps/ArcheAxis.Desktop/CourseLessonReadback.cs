using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace ArcheAxis.Desktop;

// Display only a persisted, current candidate. Starting learning remains a separate human action.
public sealed record CourseLessonReadback(string CourseId, string ArtifactId, string KnowledgeId,
    string KnowledgeVersion, string SourceId, string SourceRevision, string ItemKey,
    string Title, string LessonText, JsonElement Course)
{
    private static string Required(JsonElement value, string key) => MachineLearningJourney.Required(value, key);
    private static void True(JsonElement value, string key)
    { if (value.GetProperty(key).ValueKind != JsonValueKind.True) throw new InvalidOperationException("课件复核边界无法核验"); }

    public static void ValidateAssessment(JsonElement receipt, string itemKey, string knowledgeId, string? version)
    {
        if (Required(receipt, "item_key") != itemKey || Required(receipt, "knowledge_id") != knowledgeId
            || (version is not null && Required(receipt, "knowledge_version") != version))
            throw new InvalidOperationException("学习题目与当前知识或课件不一致，未启动学习。");
        Required(receipt, "assessment_id");
    }

    public static CourseLessonReadback Generated(JsonElement receipt, string knowledgeId)
    {
        True(receipt, "human_review_required");
        var suggestion = receipt.GetProperty("suggested_learning_item");
        var item = Stored(receipt.GetProperty("course"), Required(suggestion, "course_id"), Required(suggestion, "artifact_id"));
        if (item.KnowledgeId != knowledgeId || Required(suggestion, "knowledge_id") != knowledgeId
            || Required(suggestion, "knowledge_version") != item.KnowledgeVersion
            || Required(suggestion, "source_id") != item.SourceId
            || Required(suggestion, "source_revision") != item.SourceRevision
            || Required(suggestion, "item_key") != $"course:{item.CourseId}:artifact:{item.ArtifactId}")
            throw new InvalidOperationException("学习建议与课件来源不一致");
        return item with { ItemKey = Required(suggestion, "item_key") };
    }

    public static CourseLessonReadback Stored(JsonElement course, string courseId, string artifactId)
    {
        True(course, "human_review_required");
        if (course.GetProperty("stale").ValueKind != JsonValueKind.False || Required(course, "status") != "candidate")
            throw new InvalidOperationException("课件来源已变化或不再是待复核课件");
        var manifest = course.GetProperty("manifest");
        if (Required(manifest, "manifest_id") != courseId || Required(manifest, "status") != "candidate")
            throw new InvalidOperationException("课程读回身份不一致");
        JsonElement artifact = default;
        foreach (var candidate in manifest.GetProperty("artifacts").EnumerateArray())
            if (Required(candidate, "artifact_id") == artifactId) artifact = candidate;
        if (artifact.ValueKind != JsonValueKind.Object || Required(artifact, "artifact_type") != "lesson"
            || Required(artifact, "status") != "candidate" || Required(artifact, "renderer") != "native-lesson"
            || artifact.GetProperty("interactive").ValueKind != JsonValueKind.False)
            throw new InvalidOperationException("当前课件不是可读取的课程正文");
        // This normal flow enrolls one canonical knowledge, never an arbitrary multi-source JSON course.
        var bindings = course.GetProperty("bindings");
        if (bindings.GetArrayLength() != 1 || artifact.GetProperty("knowledge_ids").GetArrayLength() != 1)
            throw new InvalidOperationException("当前学习入口只支持单条知识课件");
        var binding = bindings[0];
        var componentId = Required(binding, "component_id");
        if (artifact.GetProperty("knowledge_ids")[0].GetString() != componentId
            || binding.GetProperty("stale").ValueKind != JsonValueKind.False)
            throw new InvalidOperationException("课件知识绑定无法核验");
        var sourceId = Required(binding, "source_id");
        if (artifact.GetProperty("source_ids").GetArrayLength() != 1 || artifact.GetProperty("source_ids")[0].GetString() != sourceId)
            throw new InvalidOperationException("课件资料来源无法核验");
        return new(courseId, artifactId, Required(binding, "knowledge_id"), Required(binding, "knowledge_version"),
            sourceId, Required(binding, "source_revision"), "", Required(artifact, "title"), "", course.Clone());
    }

    public CourseLessonReadback ReadStored(JsonElement course)
    {
        var next = Stored(course, CourseId, ArtifactId);
        if (!Equal(Course, course)) throw new InvalidOperationException("课程持久化读回已变化");
        return next with { ItemKey = ItemKey };
    }

    public CourseLessonReadback ReadRendered(JsonElement receipt)
    {
        True(receipt, "derived_only"); True(receipt, "canonical_bindings_verified"); True(receipt, "human_review_required");
        var next = ReadStored(receipt.GetProperty("course"));
        var render = receipt.GetProperty("render");
        True(render, "derived_only"); True(render, "human_review_required");
        if (Required(render, "schema") != "archeaxis.general-course-worker/v1" || Required(render, "status") != "DERIVED"
            || !Equal(render.GetProperty("manifest"), Course.GetProperty("manifest")))
            throw new InvalidOperationException("渲染结果与已保存课程不一致");
        var manifest = Course.GetProperty("manifest");
        var artifact = render.GetProperty("artifact");
        JsonElement saved = default;
        foreach (var entry in manifest.GetProperty("artifacts").EnumerateArray())
            if (Required(entry, "artifact_id") == ArtifactId) saved = entry;
        if (!Equal(artifact, saved)) throw new InvalidOperationException("渲染课件身份不一致");
        var content = Required(render.GetProperty("lesson"), "content").Replace("\r\n", "\n");
        void Match(string text) { if (!content.Contains(text.Replace("\r\n", "\n"), StringComparison.Ordinal)) throw new InvalidOperationException("课件正文与课程内容不一致"); }
        Match($"# {Title}\n"); Match($"Manifest: `{CourseId}`"); Match($"Artifact: `{ArtifactId}`");
        Match($"- `{SourceId}`");
        var text = new StringBuilder();
        var ids = new HashSet<string>(StringComparer.Ordinal);
        foreach (var id in artifact.GetProperty("knowledge_ids").EnumerateArray()) ids.Add(id.GetString()!);
        var componentCount = 0;
        foreach (var component in manifest.GetProperty("knowledge_components").EnumerateArray())
        {
            if (!ids.Contains(Required(component, "component_id"))) continue;
            var title = Required(component, "title"); var statement = Required(component, "statement");
            Match($"- `{Required(component, "component_id")}` ({Required(component, "kind")}): {title} — {statement}");
            text.AppendLine(title).AppendLine(statement).AppendLine(); componentCount++;
        }
        if (componentCount != ids.Count) throw new InvalidOperationException("课件缺少已绑定知识正文");
        text.AppendLine("学习目标");
        var objectiveCount = 0;
        foreach (var objective in manifest.GetProperty("learning_objectives").EnumerateArray())
        {
            var selected = false;
            foreach (var id in objective.GetProperty("knowledge_component_ids").EnumerateArray()) selected |= ids.Contains(id.GetString()!);
            if (!selected) continue;
            var title = Required(objective, "title"); var statement = Required(objective, "statement");
            Match($"- `{Required(objective, "objective_id")}`: {title} — {statement}");
            text.AppendLine($"• {title}：{statement}"); objectiveCount++;
        }
        if (objectiveCount == 0) throw new InvalidOperationException("课件缺少学习目标");
        return next with { LessonText = text.ToString() };
    }

    // JSON property order is irrelevant; identities, arrays and every value must still match.
    private static bool Equal(JsonElement a, JsonElement b)
    {
        if (a.ValueKind != b.ValueKind) return false;
        if (a.ValueKind == JsonValueKind.Object)
        {
            var count = 0; foreach (var p in a.EnumerateObject())
            { count++; if (!b.TryGetProperty(p.Name, out var value) || !Equal(p.Value, value)) return false; }
            var other = 0; foreach (var p in b.EnumerateObject()) other++;
            return count == other;
        }
        if (a.ValueKind == JsonValueKind.Array)
        { if (a.GetArrayLength() != b.GetArrayLength()) return false; for (var i = 0; i < a.GetArrayLength(); i++) if (!Equal(a[i], b[i])) return false; return true; }
        return a.ValueKind == JsonValueKind.String ? a.GetString() == b.GetString() : a.GetRawText() == b.GetRawText();
    }
}

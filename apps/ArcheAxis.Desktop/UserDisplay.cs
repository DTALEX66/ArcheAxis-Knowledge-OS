using System;
using System.Text.Json;

namespace ArcheAxis.Desktop;

/// <summary>Presentation only; persisted identities and backend states stay unchanged.</summary>
public static class UserDisplay
{
    public static string Status(string? value) => value?.ToLowerInvariant() switch
    {
        "accepted" => "已确认", "candidate" => "待复核", "rejected" => "未接受",
        "queued" => "等待处理", "running" => "处理中", "succeeded" => "已完成",
        "failed" or "error" => "处理失败", "cancelled" => "已取消",
        "permission" => "无访问权限", "inactive" => "已停用", _ => "状态待确认"
    };

    public static string Date(string? value) => DateTimeOffset.TryParse(value, out var date)
        ? date.ToLocalTime().ToString("yyyy-MM-dd HH:mm") : "时间未提供";

    public static string Message(string value) => value.Replace("source_id↔job_id", "来源与任务")
        .Replace("source_id", "来源标识").Replace("job_id", "任务标识")
        .Replace("knowledge_id", "知识标识").Replace("Core ", "").Replace("Core", "服务")
        .Replace("accepted Knowledge", "已确认知识").Replace("Knowledge", "知识")
        .Replace("Candidate", "待复核知识").Replace("text transform", "提取文本")
        .Replace("transform", "提取文本").Replace("Evidence anchor", "引用位置");

    public static string Failure(string? value)
    {
        if (string.IsNullOrWhiteSpace(value) || value == "—") return "处理失败，请查看详细记录。";
        var message = value.Trim();
        if (message.Contains("source_id/job_id missing", StringComparison.Ordinal)) return "资料缺少关联任务，请重新选择来源。";
        if (message.Contains("different job_id", StringComparison.Ordinal)) return "任务记录与请求不一致，请刷新后重试。";
        if (message.Contains("not bound to", StringComparison.Ordinal)) return "当前任务不属于所选资料，请重新选择来源。";
        if (message.Contains("identity is incomplete or mismatched", StringComparison.Ordinal)) return "资料来源核验失败，请重新读取。";
        if (message.Contains("did not contain string content", StringComparison.Ordinal)) return "处理结果没有可阅读的正文。";
        if (message.StartsWith("HTTP ") || message.StartsWith("transform HTTP "))
            return message.Contains("404", StringComparison.Ordinal) ? "未找到处理记录，请重新读取来源。" : "服务暂时无法提供处理结果，请稍后重试。";
        if (message.StartsWith("{") || message.StartsWith("["))
        {
            try
            {
                using var doc = JsonDocument.Parse(message);
                foreach (var key in new[] { "message", "detail", "error" })
                    if (doc.RootElement.ValueKind == JsonValueKind.Object && doc.RootElement.TryGetProperty(key, out var field)
                        && field.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(field.GetString()))
                    { message = field.GetString()!; break; }
                if (message.StartsWith("{") || message.StartsWith("[")) return "处理失败，请查看详细记录。";
            }
            catch (JsonException) { return "处理失败，请查看详细记录。"; }
        }
        var firstLine = message.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)[0];
        var readable = Message(firstLine);
        var http = readable.IndexOf("（HTTP ", StringComparison.Ordinal);
        if (http >= 0)
        {
            var end = readable.IndexOf('）', http);
            if (end > http) readable = readable.Remove(http, end - http + 1);
        }
        return readable.Length > 180 ? readable[..180] + "…" : readable;
    }
}

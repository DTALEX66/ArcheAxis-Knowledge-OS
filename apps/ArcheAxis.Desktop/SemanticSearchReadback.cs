using System;
using System.Collections.Generic;
using System.Text.Json;

namespace ArcheAxis.Desktop;

public sealed record SemanticSearchHit(string KnowledgeId, string Version, string Body, string? SourceId);
public sealed record SemanticSearchSnapshot(string Status, string RankingBasis, IReadOnlyList<SemanticSearchHit> Hits)
{
    private static string Required(JsonElement value, string key) => MachineLearningJourney.Required(value, key);

    public static SemanticSearchSnapshot Read(JsonElement root, string query)
    {
        if (Required(root, "schema") != "archeaxis.semantic-search/v1" || Required(root, "q") != query)
            throw new InvalidOperationException("搜索回执与当前查询不匹配");
        var status = Required(root, "status");
        var complete = root.GetProperty("complete").GetBoolean();
        if (status is not ("AVAILABLE" or "PARTIAL" or "UNAVAILABLE" or "EMPTY") || complete != (status == "AVAILABLE"))
            throw new InvalidOperationException("搜索完整状态不一致");
        var candidates = new Dictionary<string, SemanticSearchHit>(StringComparer.Ordinal);
        foreach (var item in root.GetProperty("candidates").EnumerateArray())
        {
            if (Required(item, "status") != "accepted") throw new InvalidOperationException("搜索返回了未确认知识");
            var id = Required(item, "knowledge_id");
            string? source = item.TryGetProperty("source_id", out var field) && field.ValueKind == JsonValueKind.String ? field.GetString() : null;
            if (!candidates.TryAdd(id, new(id, Required(item, "knowledge_version"), Required(item, "body"), source)))
                throw new InvalidOperationException("搜索返回重复知识");
        }
        if (root.GetProperty("candidate_count").GetInt32() != candidates.Count || (status == "EMPTY" && candidates.Count != 0))
            throw new InvalidOperationException("搜索范围计数不一致");
        var embedding = root.GetProperty("embedding");
        var reranker = root.GetProperty("reranker");
        var embeddingComplete = embedding.GetProperty("complete").GetBoolean();
        var rerankerComplete = reranker.GetProperty("complete").GetBoolean();
        if (complete != (embeddingComplete && rerankerComplete)) throw new InvalidOperationException("排序完整状态不一致");
        var leg = rerankerComplete ? reranker : embeddingComplete ? embedding
            : reranker.GetProperty("rank").GetArrayLength() > 0 ? reranker : embedding;
        var basis = rerankerComplete ? "语义精排" : embeddingComplete ? "语义匹配" : "部分语义排序";
        var hits = new List<SemanticSearchHit>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var row in leg.GetProperty("rank").EnumerateArray())
        {
            var id = Required(row, "knowledge_id");
            if (!seen.Add(id) || !candidates.TryGetValue(id, out var candidate)
                || Required(row, "knowledge_version") != candidate.Version)
                throw new InvalidOperationException("排序身份与已确认知识不一致");
            var score = row.GetProperty("score").GetDouble();
            if (!double.IsFinite(score)) throw new InvalidOperationException("排序回执无效");
            hits.Add(candidate);
        }
        if ((status is "EMPTY" or "UNAVAILABLE") && hits.Count > 0) throw new InvalidOperationException("不可用排序包含结果");
        if ((embeddingComplete || rerankerComplete) && hits.Count != candidates.Count)
            throw new InvalidOperationException("完整排序缺少知识");
        return new(status, basis, hits);
    }
}

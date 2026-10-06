using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using Avalonia.Interactivity;

namespace ArcheAxis.Desktop;

public partial class MainWindow
{
    private bool _semanticSearchInProgress;

    private async void OnSemanticSearchClick(object? sender, RoutedEventArgs e)
    {
        if (_semanticSearchInProgress) return;
        var query = SearchPageQueryBox.Text?.Trim() ?? "";
        if (query.Length == 0 || query.Length > 2048)
        { SetStatus(SearchPageStatusText, "请输入搜索内容（最多 2048 个字符）。", "empty"); return; }
        if (_supervisor is null || _supervisor.CoreUrl.Length == 0)
        { SetStatus(SearchPageStatusText, "服务尚未连接，暂时无法语义搜索。", "error"); return; }
        var version = ++_librarySearchRequestVersion;
        bool Current() => version == _librarySearchRequestVersion && _activeSection == "search"
            && SearchPageQueryBox.Text?.Trim() == query;
        _semanticSearchInProgress = true;
        SearchPageSemanticButton.IsEnabled = false;
        SearchPageResultsList.ItemsSource = Array.Empty<LibraryResultRow>();
        SearchPageEmptyState.IsVisible = true;
        SearchPageEmptyText.Text = "正在语义搜索，请稍候…";
        SearchPageResultCountText.Text = "正在处理…";
        SetStatus(SearchPageStatusText, "正在对当前已确认知识进行语义排序…", "loading");
        try
        {
            using var response = await _supervisor.SendAsync(HttpMethod.Post, "/api/v1/search/semantic",
                new StringContent(JsonSerializer.Serialize(new { q = query }), Encoding.UTF8, "application/json"));
            var raw = await response.Content.ReadAsStringAsync();
            if (!Current()) return;
            SearchPageDiagnosticsText.Text = $"HTTP {(int)response.StatusCode}\n{raw}";
            if (!response.IsSuccessStatusCode)
            {
                var message = IsPermissionStatus(response.StatusCode) ? "没有搜索权限，请检查当前会话。"
                    : response.StatusCode == System.Net.HttpStatusCode.Conflict ? "知识或来源已变化，请刷新后重试；也可使用关键词搜索。"
                    : "语义搜索暂不可用，请重试或使用关键词搜索。";
                SetStatus(SearchPageStatusText, message, "error");
                SearchPageEmptyText.Text = message;
                SearchPageResultCountText.Text = "搜索未完成";
                return;
            }
            using var doc = JsonDocument.Parse(raw);
            var snapshot = SemanticSearchSnapshot.Read(doc.RootElement, query);
            var rows = new List<LibraryResultRow>();
            foreach (var hit in snapshot.Hits)
                rows.Add(new("knowledge", hit.KnowledgeId, hit.SourceId ?? "", "", "accepted", "true", "", "已确认知识")
                    { Body = hit.Body, SourceTitle = hit.SourceId is null ? "来源未提供" : ResolveSourceTitle(hit.SourceId) });
            _selectedLibraryResult = null;
            SearchPageResultsList.ItemsSource = rows;
            SearchPageEmptyState.IsVisible = rows.Count == 0;
            SearchPageResultCountText.Text = $"本次返回 {rows.Count} 条知识";
            var summary = snapshot.Status switch
            {
                "AVAILABLE" => "语义排序已返回。结果来自当前已确认知识。",
                "PARTIAL" => $"语义功能部分可用，当前按{snapshot.RankingBasis}展示已返回结果；排序尚未完整完成。",
                "EMPTY" => "当前没有可参与语义搜索的已确认知识。",
                _ => "语义排序服务暂不可用，请使用关键词搜索。"
            };
            SearchPageEmptyText.Text = summary;
            SetStatus(SearchPageStatusText, summary, snapshot.Status == "AVAILABLE" ? "success" : snapshot.Status == "PARTIAL" ? "warning" : "empty");
        }
        catch (Exception)
        {
            if (!Current()) return;
            SearchPageEmptyText.Text = "语义搜索中断或返回内容无法核验，请重试或使用关键词搜索。";
            SearchPageResultCountText.Text = "搜索未完成";
            SetStatus(SearchPageStatusText, SearchPageEmptyText.Text, "error");
        }
        finally
        { _semanticSearchInProgress = false; SearchPageSemanticButton.IsEnabled = true; }
    }
}

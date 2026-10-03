using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia;
using Avalonia.Automation;
using Avalonia.Controls;
using Avalonia.Controls.Templates;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Layout;
using Avalonia.Threading;

namespace ArcheAxis.Desktop.Views;

public sealed class EvidenceAnchorRow
{
    public string AnchorId { get; }
    public string SourceId { get; }
    public string RawSha256 { get; }
    public string SourceRevision { get; }
    public string Locator { get; }
    public string CreatedAt { get; }
    public string SourceRevisionDisplay => DisplayOrDash(SourceRevision);
    public string RawSha256Display => DisplayOrDash(RawSha256);
    public string LocatorDisplay => DisplayOrDash(Locator);
    public string CreatedAtDisplay => UserDisplay.Date(CreatedAt);
    public string SourceTitle { get; set; } = "资料来源";
    /// <summary>Whether the Core named the source, rather than this window falling back to a local guess.</summary>
    public bool HasSourceName { get; private set; }
    /// <summary>
    /// The quoted selection the Core stored with the anchor, empty when the anchor only records a
    /// position. It is shown instead of a generic label because a reader who cannot see what was
    /// quoted cannot judge whether the citation is about the thing they are reading.
    /// </summary>
    public string Quote { get; private set; } = "";
    public string TitleDisplay => string.IsNullOrWhiteSpace(Quote) ? $"{SourceTitle}的引用记录" : QuoteExcerpt;
    public string PublicationYearDisplay => "年份未提供";
    public string VerificationStatusDisplay => "验证状态未提供";
    public string ConfidenceDisplay => "未提供";
    public string TopicDisplay => "未提供";
    public string CitationCountDisplay => "未提供";
    public string DisplayText => $"{TitleDisplay} · {CreatedAtDisplay}";
    public string DetailText =>
        $"anchor_id={AnchorId}\nsource_id={SourceId}\nraw_sha256={RawSha256}\nsource_revision={SourceRevision}\ncreated_at={CreatedAt}\nlocator={Locator}\n"
        + (string.IsNullOrWhiteSpace(Quote) ? string.Empty : $"quote={Quote}\n")
        + (string.IsNullOrWhiteSpace(KnowledgeId) ? string.Empty : $"knowledge_id={KnowledgeId} · status={KnowledgeStatus ?? "—"}\n")
        + "Evidence anchor 仅提供来源定位，不包含原文正文。";

    /// <summary>The Core's own file name for the material; an empty or placeholder value changes nothing.</summary>
    public void SetSourceName(string? name)
    {
        if (string.IsNullOrWhiteSpace(name) || name == "—" || name == "未暴露") return;
        SourceTitle = name;
        HasSourceName = true;
    }

    public void SetQuote(string? quote)
    {
        if (string.IsNullOrWhiteSpace(quote) || quote == "—" || quote == "未暴露") return;
        Quote = quote;
    }

    /// <summary>The knowledge row this anchor is cited by, empty when nothing cites it yet.</summary>
    public string KnowledgeId { get; private set; } = "";
    public string KnowledgeStatus { get; private set; } = "";

    public void SetKnowledgeLink(string? knowledgeId, string? status)
    {
        if (string.IsNullOrWhiteSpace(knowledgeId) || knowledgeId == "—" || knowledgeId == "未暴露") return;
        KnowledgeId = knowledgeId;
        KnowledgeStatus = string.IsNullOrWhiteSpace(status) || status == "—" ? string.Empty : status;
    }

    /// <summary>True while the cited knowledge still needs a person's decision.</summary>
    public bool IsPendingReview => string.Equals(KnowledgeStatus, "candidate", StringComparison.Ordinal);

    /// <summary>Whitespace-collapsed excerpt, because a quoted line is frequently multi-line.</summary>
    public string QuoteExcerpt
    {
        get
        {
            var flattened = Quote.Replace('\r', ' ').Replace('\n', ' ').Trim();
            while (flattened.Contains("  ", StringComparison.Ordinal))
                flattened = flattened.Replace("  ", " ", StringComparison.Ordinal);
            return flattened.Length <= 90 ? flattened : flattened[..90] + "…";
        }
    }

    public EvidenceAnchorRow(string anchorId, string sourceId, string rawSha256, string sourceRevision, string locator, string createdAt)
    {
        AnchorId = anchorId;
        SourceId = sourceId;
        RawSha256 = rawSha256;
        SourceRevision = sourceRevision;
        Locator = locator;
        CreatedAt = createdAt;
    }

    private static string DisplayOrDash(string? value) => string.IsNullOrWhiteSpace(value) ? "—" : value;

    public override string ToString() => DisplayText;
}

public sealed class EvidenceAnchorSelectedEventArgs : EventArgs
{
    public EvidenceAnchorRow Row { get; }
    public EvidenceAnchorSelectedEventArgs(EvidenceAnchorRow row) => Row = row;
}

public sealed class EvidenceAnchorDetailModeChangedEventArgs : EventArgs
{
    public bool IsOpen { get; }
    public EvidenceAnchorDetailModeChangedEventArgs(bool isOpen) => IsOpen = isOpen;
}

public partial class EvidenceCenterView : UserControl
{
    public static readonly StyledProperty<double> NarrowActionsBreakpointProperty =
        AvaloniaProperty.Register<EvidenceCenterView, double>(nameof(NarrowActionsBreakpoint), 1280);

    public event EventHandler? RefreshRequested;
    public event EventHandler<EvidenceAnchorSelectedEventArgs>? AnchorSelected;
    public event EventHandler<EvidenceAnchorDetailModeChangedEventArgs>? DetailModeChanged;
    public event EventHandler? OpenCaptureRequested;
    public event EventHandler? OpenJobsRequested;
    public event EventHandler? OpenSourceRequested;

    /// <summary>Every anchor the last read returned, before the pending-review filter is applied.</summary>
    private IReadOnlyList<EvidenceAnchorRow> _allRows = Array.Empty<EvidenceAnchorRow>();

    public EvidenceAnchorRow? SelectedAnchor => EvidenceAnchorsList.SelectedItem as EvidenceAnchorRow;
    public bool IsDetailOpen => EvidenceDetailSurface.IsVisible;

    public double NarrowActionsBreakpoint
    {
        get => GetValue(NarrowActionsBreakpointProperty);
        set => SetValue(NarrowActionsBreakpointProperty, value);
    }

    public EvidenceCenterView() => InitializeComponent();

    public void OpenCapture() => OpenCaptureRequested?.Invoke(this, EventArgs.Empty);
    public void OpenJobs() => OpenJobsRequested?.Invoke(this, EventArgs.Empty);

    public void ResetSelection()
    {
        EvidenceAnchorDetailText.Text = "尚未选择引用记录。";
        SetDetailMode(false);
        EvidenceDetailAnchorTitle.Text = "尚未选择引用记录";
        EvidenceDetailSourceText.Text = "来源和时间尚未读取";
        EvidenceDetailLocatorText.Text = "locator · Core 未暴露";
        EvidenceDetailChainText.Text = "来源链详情只展示 Core 已返回的 source、revision、hash 与 locator。";
        EvidenceChainSourceNodeText.Text = "来源尚未读取";
        EvidenceChainAnchorNodeText.Text = "引用尚未读取";
        _allRows = Array.Empty<EvidenceAnchorRow>();
        // Clearing the filter re-enters the filter through its own change handler; the empty row
        // set above makes that a no-op rather than a repopulation of a reset list.
        if (EvidencePendingOnlyCheck is not null) EvidencePendingOnlyCheck.IsChecked = false;
        EvidenceAnchorsList.ItemsSource = null;
        EvidenceEmptyState.IsVisible = true;
        EvidenceEmptyTitleText.Text = "尚未读取引用记录";
        // Say plainly that an empty surface stays empty: this window never fills a missing
        // projection with sample rows, which is the guarantee a reader needs to trust the list.
        EvidenceEmptyDescriptionText.Text = "点击“读取证据”查看已保存的来源引用。未生成示例记录，缺失字段保持未提供。";
        EvidenceCountMetricText.Text = "—";
        EvidenceSourceMetricText.Text = "—";
        EvidenceCountMetricText.Classes.Set("metric-unknown", true);
        EvidenceSourceMetricText.Classes.Set("metric-unknown", true);
        EvidenceCountMetricLabel.Text = "证据 · 尚未读取";
        EvidenceSourceMetricLabel.Text = "来源 · 尚未读取";
    }

    public void SetAnchors(IReadOnlyList<EvidenceAnchorRow> rows)
    {
        // Every row is kept so the pending-review filter can be applied and lifted without a
        // second read of the Core; the metrics below always describe the whole projection.
        _allRows = rows;
        ApplyPendingFilter();
        EvidenceCountMetricText.Text = rows.Count.ToString(System.Globalization.CultureInfo.InvariantCulture);
        EvidenceSourceMetricText.Text = rows.Select(row => row.SourceId).Distinct(StringComparer.Ordinal).Count()
            .ToString(System.Globalization.CultureInfo.InvariantCulture);
        EvidenceCountMetricText.Classes.Set("metric-unknown", false);
        EvidenceSourceMetricText.Classes.Set("metric-unknown", false);
        EvidenceCountMetricLabel.Text = "证据";
        EvidenceSourceMetricLabel.Text = "来源";
        EvidenceVerifiedMetricText.Text = "—";
        // A real count of anchors whose knowledge row is still awaiting a human decision, instead
        // of a placeholder that never changes. It stays "no data" rather than zero when empty.
        var pendingReview = rows.Count(row => row.IsPendingReview);
        EvidenceReviewMetricText.Text = pendingReview == 0
            ? "—"
            : pendingReview.ToString(System.Globalization.CultureInfo.InvariantCulture);
        EvidenceReviewMetricText.Classes.Set("metric-unknown", pendingReview == 0);
        EvidenceReviewMetricLabel.Text = pendingReview == 0 ? "待复核 · 暂无数据" : "待复核";
        if (rows.Count == 0)
        {
            EvidenceEmptyTitleText.Text = "暂无引用记录";
            EvidenceEmptyDescriptionText.Text = "暂无已保存引用。可导入资料，或查看资料处理任务。未生成示例记录，缺失字段保持未提供。";
        }
    }

    /// <summary>
    /// Show only the rows whose cited knowledge still awaits a person, or all of them. The
    /// predicate reads the Core's own knowledge status, so the filter can never invent a
    /// pending item; when nothing matches it says so instead of showing an empty table.
    /// </summary>
    private void ApplyPendingFilter()
    {
        var pendingOnly = EvidencePendingOnlyCheck?.IsChecked == true;
        var visible = pendingOnly ? _allRows.Where(row => row.IsPendingReview).ToList() : _allRows;
        EvidenceAnchorsList.ItemsSource = visible;
        EvidenceEmptyState.IsVisible = visible.Count == 0;
        if (visible.Count == 0 && pendingOnly)
        {
            EvidenceEmptyTitleText.Text = "没有待复核的引用记录";
            EvidenceEmptyDescriptionText.Text = "当前没有引用了待复核知识的记录。取消“仅看待复核”可看到全部引用。";
        }
    }

    private void OnPendingOnlyChanged(object? sender, RoutedEventArgs e) => ApplyPendingFilter();

    public void SetStatus(string text, string semanticClass)
    {
        EvidenceStatusText.Text = text;
        AutomationProperties.SetName(EvidenceStatusText, text);
        foreach (var item in new[] { "loading", "empty", "error", "permission", "success", "info" })
            EvidenceStatusText.Classes.Set($"status-{item}", string.Equals(item, semanticClass, StringComparison.Ordinal));
    }

    public void SetBundlesText(string text) => EvidenceBundlesText.Text = text;
    public string BundlesText => EvidenceBundlesText.Text ?? string.Empty;
    public void SetAnchorDetail(string text) => EvidenceAnchorDetailText.Text = text;
    public void SetRefreshEnabled(bool enabled) => EvidenceRefreshButton.IsEnabled = enabled;

    public void SetResponsiveLayout(bool compact, double width)
    {
        var narrowActions = width < NarrowActionsBreakpoint;
        var metricColumns = width < 420 ? 1 : width < 900 ? 2 : 4;
        var metricCards = EvidenceMetricsGrid.Children.OfType<Border>().ToArray();
        EvidenceMetricsGrid.ColumnDefinitions = new ColumnDefinitions(string.Join(",", Enumerable.Repeat("*", metricColumns)));
        EvidenceMetricsGrid.RowDefinitions = new RowDefinitions(string.Join(",", Enumerable.Repeat("Auto", (metricCards.Length + metricColumns - 1) / metricColumns)));
        for (var index = 0; index < metricCards.Length; index++)
        {
            var metricCard = metricCards[index];
            Grid.SetColumn(metricCard, index % metricColumns);
            Grid.SetRow(metricCard, index / metricColumns);
            metricCard.Padding = width < 760 ? new Thickness(7) : width < 1280 ? new Thickness(10) : new Thickness(18);
        }
        EvidenceEmptyStateContent.Orientation = Orientation.Horizontal;
        EvidenceEmptyActions.Orientation = narrowActions ? Orientation.Vertical : Orientation.Horizontal;
        EvidenceEmptyStateImage.Width = 64;
        EvidenceEmptyStateImage.Height = 64;
        if (width < 1280)
        {
            var emptyIconSize = width < 760 ? 24 : 40;
            EvidenceEmptyStateImage.Width = emptyIconSize;
            EvidenceEmptyStateImage.Height = emptyIconSize;
        }
        if (EvidenceEmptyStateImage.Child is AaosIcon emptyIcon)
            emptyIcon.Width = emptyIcon.Height = Math.Min(28, Math.Max(14, EvidenceEmptyStateImage.Width * 0.4375));
        EvidenceEmptyStateImage.HorizontalAlignment = HorizontalAlignment.Left;
        EvidenceToolbar.ColumnDefinitions = narrowActions ? new ColumnDefinitions("*") : new ColumnDefinitions("Auto,*");
        EvidenceToolbarActions.Orientation = narrowActions ? Orientation.Vertical : Orientation.Horizontal;
        EvidenceToolbar.RowDefinitions = narrowActions ? new RowDefinitions("Auto,Auto") : new RowDefinitions("Auto");
        Grid.SetColumn(EvidenceStatusText, narrowActions ? 0 : 1);
        Grid.SetRow(EvidenceStatusText, narrowActions ? 1 : 0);
        EvidenceAnchorsList.MaxHeight = compact ? 320 : 560;
        EvidenceCategoryTabs.Spacing = width < 760 ? 4 : 8;
        var detailColumns = width < 1024 ? 1 : 2;
        EvidenceDetailPageGrid.ColumnDefinitions = detailColumns == 1
            ? new ColumnDefinitions("*")
            : new ColumnDefinitions("1.1*,1*");
        EvidenceDetailPageGrid.RowDefinitions = detailColumns == 1
            ? new RowDefinitions("Auto,Auto")
            : new RowDefinitions("Auto");
        Grid.SetColumn(EvidenceDetailPageGrid.Children[1], detailColumns == 1 ? 0 : 1);
        Grid.SetRow(EvidenceDetailPageGrid.Children[1], detailColumns == 1 ? 1 : 0);
        var chainIllustrationSize = Math.Max(0, Math.Min(300, width - 48));
        EvidenceSourceChainIllustration.Width = chainIllustrationSize;
        EvidenceSourceChainIllustration.Height = chainIllustrationSize;
        EvidenceLibraryTableHeader.IsVisible = width >= 1120;
        EvidenceAnchorsList.ItemTemplate = (IDataTemplate)Resources[
            width < 1120 ? "EvidenceLibraryCompactRowTemplate" : "EvidenceLibraryRowTemplate"]!;
    }

    private void OnRefreshClick(object? sender, RoutedEventArgs e) => RefreshRequested?.Invoke(this, EventArgs.Empty);
    private void OnOpenCaptureClick(object? sender, RoutedEventArgs e) => OpenCaptureRequested?.Invoke(this, EventArgs.Empty);
    private void OnOpenJobsClick(object? sender, RoutedEventArgs e) => OpenJobsRequested?.Invoke(this, EventArgs.Empty);

    private void OnAnchorSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (e.AddedItems.Count == 1 && e.AddedItems[0] is EvidenceAnchorRow row)
        {
            EvidenceDetailAnchorTitle.Text = row.TitleDisplay;
            EvidenceDetailSourceText.Text = $"来源：{row.SourceTitle} · 保存于 {row.CreatedAtDisplay}";
            EvidenceDetailLocatorText.Text = $"locator · {row.Locator}";
            EvidenceDetailChainText.Text = row.DetailText;
            EvidenceChainSourceNodeText.Text = row.SourceTitle;
            EvidenceChainAnchorNodeText.Text = "已保存引用位置";
            SetDetailMode(true);
            AnchorSelected?.Invoke(this, new EvidenceAnchorSelectedEventArgs(row));
        }
    }

    private void OnBackToEvidenceClick(object? sender, RoutedEventArgs e)
    {
        SetDetailMode(false);
        Dispatcher.UIThread.Post(() => EvidenceAnchorsList.Focus(), DispatcherPriority.Render);
    }

    private void SetDetailMode(bool isOpen)
    {
        var changed = EvidenceDetailSurface.IsVisible != isOpen;
        if (changed && isOpen)
        {
            EvidenceDetailSurface.Opacity = 0;
            EvidenceSurface.IsVisible = false;
            EvidenceDetailSurface.IsVisible = true;
            Dispatcher.UIThread.Post(() => EvidenceDetailSurface.Opacity = 1, DispatcherPriority.Render);
        }
        else if (changed)
        {
            EvidenceDetailSurface.IsVisible = false;
            EvidenceSurface.Opacity = 0;
            EvidenceSurface.IsVisible = true;
            Dispatcher.UIThread.Post(() => EvidenceSurface.Opacity = 1, DispatcherPriority.Render);
        }
        if (changed)
            DetailModeChanged?.Invoke(this, new EvidenceAnchorDetailModeChangedEventArgs(isOpen));
    }

    private void OnOpenSelectedSourceClick(object? sender, RoutedEventArgs e)
    {
        if (SelectedAnchor is not null)
            OpenSourceRequested?.Invoke(this, EventArgs.Empty);
    }

    private void OnAnchorListKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key != Key.Enter) return;
        OpenSourceRequested?.Invoke(this, EventArgs.Empty);
        e.Handled = true;
    }

    private void OnAnchorDoubleTapped(object? sender, TappedEventArgs e)
    {
        OpenSourceRequested?.Invoke(this, EventArgs.Empty);
        e.Handled = true;
    }
}

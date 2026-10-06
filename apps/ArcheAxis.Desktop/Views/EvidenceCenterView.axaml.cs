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
    public string CreatedAtDisplay => DisplayOrDash(CreatedAt);
    // Evidence anchor IDs are the only title-like identity currently returned by Core.
    public string TitleDisplay => AnchorId;
    public string PublicationYearDisplay => "年份未由 Core 暴露";
    public string VerificationStatusDisplay => "验证状态未由 Core 暴露";
    public string ConfidenceDisplay => "Core 未暴露";
    public string TopicDisplay => "Core 未暴露";
    public string CitationCountDisplay => "Core 未暴露";
    public string DisplayText => $"{AnchorId} · source={SourceId} · revision={SourceRevision}";
    public string DetailText =>
        $"anchor_id={AnchorId}\nsource_id={SourceId}\nraw_sha256={RawSha256}\nsource_revision={SourceRevision}\ncreated_at={CreatedAt}\nlocator={Locator}\n" +
        "Evidence anchor 仅提供来源定位，不包含原文正文。";

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
        EvidenceAnchorDetailText.Text = "尚未选择 Evidence anchor。";
        SetDetailMode(false);
        EvidenceDetailAnchorTitle.Text = "尚未选择 Evidence anchor";
        EvidenceDetailSourceText.Text = "来源 / 修订 / 时间：Core 未暴露";
        EvidenceDetailLocatorText.Text = "locator · Core 未暴露";
        EvidenceDetailChainText.Text = "来源链详情只展示 Core 已返回的 source、revision、hash 与 locator。";
        EvidenceChainSourceNodeText.Text = "Core source_id 未读取";
        EvidenceChainAnchorNodeText.Text = "Core anchor_id 未读取";
        EvidenceAnchorsList.ItemsSource = null;
        EvidenceEmptyState.IsVisible = true;
        EvidenceEmptyTitleText.Text = "尚未读取 Evidence anchor";
        EvidenceEmptyDescriptionText.Text = "点击“读取证据”读取 Core 已持久化的来源定位；页面不使用演示数据填充。";
        EvidenceCountMetricText.Text = "—";
        EvidenceSourceMetricText.Text = "—";
        EvidenceCountMetricText.Classes.Set("metric-unknown", true);
        EvidenceSourceMetricText.Classes.Set("metric-unknown", true);
        EvidenceCountMetricLabel.Text = "证据 · 尚未读取";
        EvidenceSourceMetricLabel.Text = "来源 · 尚未读取";
    }

    public void SetAnchors(IReadOnlyList<EvidenceAnchorRow> rows)
    {
        EvidenceAnchorsList.ItemsSource = rows;
        EvidenceEmptyState.IsVisible = rows.Count == 0;
        EvidenceCountMetricText.Text = rows.Count.ToString(System.Globalization.CultureInfo.InvariantCulture);
        EvidenceSourceMetricText.Text = rows.Select(row => row.SourceId).Distinct(StringComparer.Ordinal).Count()
            .ToString(System.Globalization.CultureInfo.InvariantCulture);
        EvidenceCountMetricText.Classes.Set("metric-unknown", false);
        EvidenceSourceMetricText.Classes.Set("metric-unknown", false);
        EvidenceCountMetricLabel.Text = "证据";
        EvidenceSourceMetricLabel.Text = "来源";
        EvidenceVerifiedMetricText.Text = "—";
        EvidenceReviewMetricText.Text = "—";
        if (rows.Count == 0)
        {
            EvidenceEmptyTitleText.Text = "暂无 Evidence anchor";
            EvidenceEmptyDescriptionText.Text = "Core 已返回空的 anchor 列表。可前往捕获来源或查看任务回执；未生成示例记录。";
        }
    }

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
            EvidenceDetailAnchorTitle.Text = row.AnchorId;
            EvidenceDetailSourceText.Text = $"来源：{row.SourceId}  ·  修订：{row.SourceRevision}  ·  创建：{row.CreatedAt}";
            EvidenceDetailLocatorText.Text = $"locator · {row.Locator}";
            EvidenceDetailChainText.Text = row.DetailText;
            EvidenceChainSourceNodeText.Text = row.SourceId;
            EvidenceChainAnchorNodeText.Text = row.AnchorId;
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

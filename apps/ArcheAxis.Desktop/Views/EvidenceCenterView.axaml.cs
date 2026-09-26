using System;
using System.Collections.Generic;
using Avalonia;
using Avalonia.Automation;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Layout;

namespace ArcheAxis.Desktop.Views;

public sealed class EvidenceAnchorRow
{
    public string AnchorId { get; }
    public string SourceId { get; }
    public string RawSha256 { get; }
    public string SourceRevision { get; }
    public string Locator { get; }
    public string DisplayText => $"{AnchorId} · source={SourceId} · revision={SourceRevision}";
    public string DetailText =>
        $"anchor_id={AnchorId}\nsource_id={SourceId}\nraw_sha256={RawSha256}\nsource_revision={SourceRevision}\nlocator={Locator}\n" +
        "Evidence anchor 仅提供来源定位，不包含原文正文。";

    public EvidenceAnchorRow(string anchorId, string sourceId, string rawSha256, string sourceRevision, string locator)
    {
        AnchorId = anchorId;
        SourceId = sourceId;
        RawSha256 = rawSha256;
        SourceRevision = sourceRevision;
        Locator = locator;
    }

    public override string ToString() => DisplayText;
}

public sealed class EvidenceAnchorSelectedEventArgs : EventArgs
{
    public EvidenceAnchorRow Row { get; }
    public EvidenceAnchorSelectedEventArgs(EvidenceAnchorRow row) => Row = row;
}

public partial class EvidenceCenterView : UserControl
{
    public static readonly StyledProperty<double> NarrowActionsBreakpointProperty =
        AvaloniaProperty.Register<EvidenceCenterView, double>(nameof(NarrowActionsBreakpoint), 1280);

    public event EventHandler? RefreshRequested;
    public event EventHandler<EvidenceAnchorSelectedEventArgs>? AnchorSelected;
    public event EventHandler? OpenCaptureRequested;
    public event EventHandler? OpenJobsRequested;
    public event EventHandler? OpenSourceRequested;

    public EvidenceAnchorRow? SelectedAnchor => EvidenceAnchorsList.SelectedItem as EvidenceAnchorRow;

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
        EvidenceAnchorsList.ItemsSource = null;
        EvidenceEmptyState.IsVisible = true;
    }

    public void SetAnchors(IReadOnlyList<EvidenceAnchorRow> rows)
    {
        EvidenceAnchorsList.ItemsSource = rows;
        EvidenceEmptyState.IsVisible = rows.Count == 0;
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
        EvidenceEmptyStateContent.Orientation = compact ? Orientation.Vertical : Orientation.Horizontal;
        EvidenceEmptyStateImage.Width = compact ? 112 : 150;
        EvidenceEmptyStateImage.HorizontalAlignment = compact ? HorizontalAlignment.Center : HorizontalAlignment.Left;
        EvidenceToolbar.ColumnDefinitions = narrowActions ? new ColumnDefinitions("*") : new ColumnDefinitions("Auto,*");
        EvidenceToolbar.RowDefinitions = narrowActions ? new RowDefinitions("Auto,Auto") : new RowDefinitions("Auto");
        Grid.SetColumn(EvidenceStatusText, narrowActions ? 0 : 1);
        Grid.SetRow(EvidenceStatusText, narrowActions ? 1 : 0);
    }

    private void OnRefreshClick(object? sender, RoutedEventArgs e) => RefreshRequested?.Invoke(this, EventArgs.Empty);
    private void OnOpenCaptureClick(object? sender, RoutedEventArgs e) => OpenCaptureRequested?.Invoke(this, EventArgs.Empty);
    private void OnOpenJobsClick(object? sender, RoutedEventArgs e) => OpenJobsRequested?.Invoke(this, EventArgs.Empty);

    private void OnAnchorSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (e.AddedItems.Count == 1 && e.AddedItems[0] is EvidenceAnchorRow row)
            AnchorSelected?.Invoke(this, new EvidenceAnchorSelectedEventArgs(row));
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

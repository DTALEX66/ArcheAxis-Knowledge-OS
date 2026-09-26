using System;
using System.Collections.Generic;
using Avalonia;
using Avalonia.Automation;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Layout;

namespace ArcheAxis.Desktop.Views;

public enum SourceReaderPresentation
{
    Empty,
    Loading,
    Members,
    SingleSourceReady,
    Pending,
    Failed,
    Mismatched,
}

public abstract class SourceReaderRow
{
    public string SourceId { get; }
    public string JobId { get; }
    public abstract string DisplayKind { get; }
    public abstract string DisplayBoundary { get; }
    public abstract string DisplayText { get; }

    protected SourceReaderRow(string sourceId, string jobId)
    {
        SourceId = sourceId;
        JobId = jobId;
    }

    public override string ToString() => DisplayText;
}

public sealed class SourceMemberRow : SourceReaderRow
{
    public string Member { get; }
    public string OriginalName { get; }
    public string Sha256 { get; }
    public string Readable { get; }
    public override string DisplayKind => "容器成员 · Core projection";
    public override string DisplayBoundary => "原文正文未在此列表中展示";
    public override string DisplayText => $"{(string.IsNullOrWhiteSpace(OriginalName) ? Member : OriginalName)} · readable={Readable} · job={JobId}";

    public SourceMemberRow(string sourceId, string member, string originalName, string sha256, string readable, string jobId)
        : base(sourceId, jobId)
    {
        Member = member;
        OriginalName = originalName;
        Sha256 = sha256;
        Readable = readable;
    }
}

public sealed class SourceJobRow : SourceReaderRow
{
    public string Kind { get; }
    public string State { get; }
    public string Attempt { get; }
    public string Error { get; }
    public bool CanReadText => Kind == "text" && State == "succeeded";
    public override string DisplayKind => $"Core 持久任务 · {Kind}";
    public override string DisplayBoundary => $"state={State} · attempt={Attempt} · error={Error}";
    public override string DisplayText => $"{Kind} · {State} · attempt={Attempt} · {JobId}" + (Error == "—" ? string.Empty : $" · {Error}");

    public SourceJobRow(string sourceId, string jobId, string kind, string state, string attempt, string error)
        : base(sourceId, jobId)
    {
        Kind = kind;
        State = state;
        Attempt = attempt;
        Error = error;
    }
}

public sealed record SourceReaderViewState(
    SourceReaderPresentation Presentation,
    string SourceId,
    IReadOnlyList<SourceReaderRow> Rows,
    SourceReaderRow? SelectedRow,
    string Summary,
    string CoreNote,
    string StatusText,
    string StatusClass,
    string TransformText,
    string ChainBoundaryText,
    bool IsLoading,
    bool CanReturnToLibrary,
    bool CanReturnToKnowledge)
{
    public static SourceReaderViewState Initial { get; } = new(
        SourceReaderPresentation.Empty,
        string.Empty,
        Array.Empty<SourceReaderRow>(),
        null,
        "输入 source_id 后读取 Core。",
        "Core 语义边界：尚未读取。",
        "尚未读取 Core 来源成员。",
        "empty",
        "尚未读取转换输出；原文正文仍未暴露。",
        string.Empty,
        false,
        false,
        false);
}

public sealed class SourceReaderLoadRequestedEventArgs : EventArgs
{
    public string SourceId { get; }
    public SourceReaderLoadRequestedEventArgs(string sourceId) => SourceId = sourceId;
}

public sealed class SourceReaderRowSelectedEventArgs : EventArgs
{
    public SourceReaderRow Row { get; }
    public SourceReaderRowSelectedEventArgs(SourceReaderRow row) => Row = row;
}

public sealed class SourceReaderRowActionEventArgs : EventArgs
{
    public SourceReaderRow? Row { get; }
    public SourceReaderRowActionEventArgs(SourceReaderRow? row) => Row = row;
}

public sealed class SourceBoundCandidateRequestedEventArgs : EventArgs
{
    public SourceReaderRow Row { get; }
    public string Body { get; }
    public string Quote { get; }
    public int SelectionStartUtf16 { get; }
    public int SelectionEndUtf16 { get; }
    public long TransformId { get; }
    public string RawSha256 { get; }

    public SourceBoundCandidateRequestedEventArgs(SourceReaderRow row, string body, string quote, int start, int end, long transformId, string rawSha256)
    {
        Row = row;
        Body = body;
        Quote = quote;
        SelectionStartUtf16 = start;
        SelectionEndUtf16 = end;
        TransformId = transformId;
        RawSha256 = rawSha256;
    }
}

public partial class SourceReaderView : UserControl
{
    public static readonly StyledProperty<double> StackBreakpointProperty =
        AvaloniaProperty.Register<SourceReaderView, double>(nameof(StackBreakpoint), 1200);
    public static readonly StyledProperty<double> NarrowActionsBreakpointProperty =
        AvaloniaProperty.Register<SourceReaderView, double>(nameof(NarrowActionsBreakpoint), 760);

    private SourceReaderViewState _state = SourceReaderViewState.Initial;
    private bool _applyingState;

    public double StackBreakpoint
    {
        get => GetValue(StackBreakpointProperty);
        set => SetValue(StackBreakpointProperty, value);
    }

    public double NarrowActionsBreakpoint
    {
        get => GetValue(NarrowActionsBreakpointProperty);
        set => SetValue(NarrowActionsBreakpointProperty, value);
    }

    public event EventHandler<SourceReaderLoadRequestedEventArgs>? LoadRequested;
    public event EventHandler<SourceReaderRowSelectedEventArgs>? RowSelected;
    public event EventHandler<SourceReaderRowActionEventArgs>? ReadTransformRequested;
    public event EventHandler<SourceReaderRowActionEventArgs>? OpenJobRequested;
    public event EventHandler<SourceReaderRowActionEventArgs>? LibraryLookupRequested;
    public event EventHandler<SourceReaderRowActionEventArgs>? CopyProvenanceRequested;
    public event EventHandler<SourceReaderRowActionEventArgs>? CopyCitationRequested;
    public event EventHandler<SourceBoundCandidateRequestedEventArgs>? SourceBoundCandidateRequested;
    public event EventHandler? ReturnToLibraryRequested;
    public event EventHandler? ReturnToKnowledgeRequested;

    public SourceReaderViewState State
    {
        get => _state;
        set
        {
            _state = value ?? SourceReaderViewState.Initial;
            ApplyState();
        }
    }

    public string SourceId
    {
        get => SourceReaderIdBox.Text?.Trim() ?? string.Empty;
        set
        {
            SourceReaderIdBox.Text = value ?? string.Empty;
            _state = _state with { SourceId = value ?? string.Empty };
        }
    }

    public SourceReaderRow? SelectedRow => SourceReaderMembersList.SelectedItem as SourceReaderRow;
    public long? LoadedTransformId { get; private set; }
    public string? LoadedRawSha256 { get; private set; }

    public SourceReaderView()
    {
        InitializeComponent();
        ApplyState();
    }

    private void ApplyState()
    {
        _applyingState = true;
        try
        {
            if (!string.Equals(SourceReaderIdBox.Text, _state.SourceId, StringComparison.Ordinal))
                SourceReaderIdBox.Text = _state.SourceId;
            SourceReaderLoadButton.IsEnabled = !_state.IsLoading;
            SourceReaderIdBox.IsEnabled = !_state.IsLoading;
            SourceReaderResultsText.Text = _state.Summary;
            SourceReaderCoreNoteText.Text = _state.CoreNote;
            SetStatus(_state.StatusText, _state.StatusClass);
            SourceReaderTransformText.Text = _state.TransformText;
            BackToLibraryButton.IsEnabled = _state.CanReturnToLibrary;
            BackToKnowledgeFromSourceButton.IsEnabled = _state.CanReturnToKnowledge;
            if (!ReferenceEquals(SourceReaderMembersList.ItemsSource, _state.Rows))
                SourceReaderMembersList.ItemsSource = _state.Rows;
            if (!ReferenceEquals(SourceReaderMembersList.SelectedItem, _state.SelectedRow))
                SourceReaderMembersList.SelectedItem = _state.SelectedRow;
            RenderSelection(_state.SelectedRow);
            if (!string.IsNullOrWhiteSpace(_state.ChainBoundaryText))
                SourceReaderChainBoundaryText.Text = _state.ChainBoundaryText;
        }
        finally
        {
            _applyingState = false;
        }
    }

    public void SetTransformIdentity(long? transformId, string? rawSha256)
    {
        LoadedTransformId = transformId;
        LoadedRawSha256 = rawSha256;
        UpdateCandidateAction();
    }

    private void SetStatus(string text, string semanticClass)
    {
        SourceReaderStatusText.Text = text;
        AutomationProperties.SetName(SourceReaderStatusText, text);
        foreach (var item in new[] { "loading", "empty", "error", "permission", "success", "info" })
            SourceReaderStatusText.Classes.Set($"status-{item}", string.Equals(item, semanticClass, StringComparison.Ordinal));
    }

    private void RenderSelection(SourceReaderRow? row)
    {
        if (row is SourceJobRow job)
        {
            SourceReaderMemberFieldLabel.Text = "来源类型";
            SourceReaderOriginalNameFieldLabel.Text = "文件名";
            SourceReaderReadableFieldLabel.Text = "输出可读性";
            SourceReaderJobFieldLabel.Text = "Core 持久任务";
            SourceReaderShaFieldLabel.Text = "来源 SHA-256";
            ViewSourceJobButton.Content = "查看选中任务回执";
            AutomationProperties.SetName(ViewSourceJobButton, "查看选中任务回执");
            ViewSourceJobButton.IsEnabled = HasValue(job.JobId);
            FindLibraryFromSourceButton.IsEnabled = false;
            SourceReaderSelectedText.Text = $"普通来源持久任务\nsource_id：{job.SourceId}\njob_id：{job.JobId}\nkind：{job.Kind}\nstate：{job.State}\nattempt：{job.Attempt}\nerror：{job.Error}";
            SourceReaderMemberFieldText.Text = "普通来源（非容器成员）";
            SourceReaderOriginalNameFieldText.Text = "由 Core 持久任务关联；文件名未由此投影提供";
            SourceReaderReadableFieldText.Text = job.CanReadText ? "成功 text 输出可读取" : $"不可读取（{job.State}/{job.Kind}）";
            SourceReaderJobFieldText.Text = job.JobId;
            SourceReaderShaFieldText.Text = "该任务投影未暴露 SHA-256";
            SourceReaderMemberBoundaryText.Text = "以下正文若存在，仅为 Core text transform 输出；不是原始字节或已接受 Knowledge。";
            ReadSourceTransformButton.IsEnabled = job.CanReadText;
            UpdateCandidateAction();
            CopySourceProvenanceButton.IsEnabled = false;
            CopySourceCitationButton.IsEnabled = false;
            SourceReaderChainSourceText.Text = $"普通来源：{job.SourceId}";
            SourceReaderChainMemberText.Text = "非容器成员；未创建伪造成员记录";
            SourceReaderChainJobText.Text = $"Core 持久任务：{job.JobId} · {job.State}";
            SourceReaderChainShaText.Text = "任务投影未提供来源摘要";
            SourceReaderChainBoundaryText.Text = "Core job.input_ref 绑定来源；转换输出不等于原件或 accepted Knowledge。";
            return;
        }

        if (row is SourceMemberRow member)
        {
            SourceReaderMemberFieldLabel.Text = "容器成员";
            SourceReaderOriginalNameFieldLabel.Text = "原件名称";
            SourceReaderReadableFieldLabel.Text = "成员可读性";
            SourceReaderJobFieldLabel.Text = "成员任务";
            SourceReaderShaFieldLabel.Text = "成员 SHA-256";
            ViewSourceJobButton.Content = "查看成员任务回执";
            AutomationProperties.SetName(ViewSourceJobButton, "查看选中容器成员的任务回执");
            ViewSourceJobButton.IsEnabled = HasValue(member.JobId);
            FindLibraryFromSourceButton.IsEnabled = HasValue(member.SourceId);
            SourceReaderSelectedText.Text = $"source_id：{member.SourceId}\nmember：{member.Member}\noriginal_name：{member.OriginalName}\nreadable：{member.Readable}\njob_id：{member.JobId}\nsha256：{member.Sha256}";
            SourceReaderMemberFieldText.Text = member.Member;
            SourceReaderOriginalNameFieldText.Text = member.OriginalName;
            SourceReaderReadableFieldText.Text = member.Readable;
            SourceReaderJobFieldText.Text = member.JobId;
            SourceReaderShaFieldText.Text = member.Sha256;
            SourceReaderMemberBoundaryText.Text = "原文正文未暴露；字段来自 Core 来源成员投影。";
            ReadSourceTransformButton.IsEnabled = string.Equals(member.Readable, "true", StringComparison.OrdinalIgnoreCase) && HasValue(member.JobId);
            UpdateCandidateAction();
            var canCopy = HasValue(member.SourceId) && HasValue(member.Member) && HasValue(member.Sha256);
            CopySourceProvenanceButton.IsEnabled = canCopy;
            CopySourceCitationButton.IsEnabled = canCopy;
            SourceReaderChainSourceText.Text = $"容器来源：{member.SourceId}";
            SourceReaderChainMemberText.Text = $"成员：{member.Member} · {member.OriginalName}";
            SourceReaderChainJobText.Text = $"处理任务：{member.JobId}";
            SourceReaderChainShaText.Text = $"内容指纹：{member.Sha256}";
            SourceReaderChainBoundaryText.Text = "仅为 Core 来源成员投影；readable 不代表已理解，sha256 不是正文或 anchor。";
            return;
        }

        SourceReaderMemberFieldLabel.Text = "成员类型";
        SourceReaderOriginalNameFieldLabel.Text = "原件名称";
        SourceReaderReadableFieldLabel.Text = "成员可读性";
        SourceReaderJobFieldLabel.Text = "成员任务";
        SourceReaderShaFieldLabel.Text = "成员 SHA-256";
        SourceReaderSelectedText.Text = "尚未选择来源成员或持久任务。";
        SourceReaderMemberFieldText.Text = "未选择";
        SourceReaderOriginalNameFieldText.Text = "未选择";
        SourceReaderReadableFieldText.Text = "未选择";
        SourceReaderJobFieldText.Text = "未选择";
        SourceReaderShaFieldText.Text = "未选择";
        SourceReaderMemberBoundaryText.Text = "原文正文未暴露；字段来自 Core 来源成员投影。";
        ReadSourceTransformButton.IsEnabled = false;
        SetTransformIdentity(null, null);
        ViewSourceJobButton.IsEnabled = false;
        FindLibraryFromSourceButton.IsEnabled = false;
        CopySourceProvenanceButton.IsEnabled = false;
        CopySourceCitationButton.IsEnabled = false;
        SourceReaderChainSourceText.Text = string.IsNullOrWhiteSpace(_state.SourceId) ? "容器来源：未读取" : $"容器来源：{_state.SourceId}";
        SourceReaderChainMemberText.Text = "成员：未选择";
        SourceReaderChainJobText.Text = "处理任务：未选择";
        SourceReaderChainShaText.Text = "内容指纹：未选择";
        SourceReaderChainBoundaryText.Text = "仅为 Core 来源成员投影；不代表正文、理解或证据 anchor。";
    }

    private static bool HasValue(string value) => !string.IsNullOrWhiteSpace(value) && value != "—";

    private void OnLoadClick(object? sender, RoutedEventArgs e) =>
        LoadRequested?.Invoke(this, new SourceReaderLoadRequestedEventArgs(SourceId));

    private void OnSourceIdKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key != Key.Enter)
            return;
        OnLoadClick(sender, new RoutedEventArgs());
        e.Handled = true;
    }

    private void OnRowSelected(object? sender, SelectionChangedEventArgs e)
    {
        if (_applyingState || SourceReaderMembersList.SelectedItem is not SourceReaderRow row)
            return;
        SetTransformIdentity(null, null);
        SetCandidateStatus("尚未创建来源关联 Candidate。", "empty");
        var transform = row switch
        {
            SourceJobRow job when job.CanReadText => "已选择 Core 成功 text 任务；点击“读取转换内容”获取持久化输出。",
            SourceJobRow job when job.Error == "—" => $"任务状态 {job.State}；成功的 text 任务才可读取。",
            SourceJobRow job => $"任务状态 {job.State}：{job.Error}",
            _ => "尚未读取转换输出；原文正文仍未暴露。",
        };
        _state = _state with { SelectedRow = row, TransformText = transform, ChainBoundaryText = string.Empty };
        SourceReaderTransformText.Text = transform;
        RenderSelection(row);
        RowSelected?.Invoke(this, new SourceReaderRowSelectedEventArgs(row));
    }

    private void OnReadTransformClick(object? sender, RoutedEventArgs e) =>
        ReadTransformRequested?.Invoke(this, new SourceReaderRowActionEventArgs(SelectedRow));

    private void OnCreateSourceBoundCandidateClick(object? sender, RoutedEventArgs e)
    {
        var row = SelectedRow;
        var quote = SourceReaderTransformText.SelectedText;
        var start = SourceReaderTransformText.SelectionStart;
        var end = SourceReaderTransformText.SelectionEnd;
        if (string.IsNullOrWhiteSpace(quote))
        {
            quote = SourceReaderQuoteBox.Text ?? string.Empty;
            if (!string.IsNullOrWhiteSpace(quote))
            {
                var transform = SourceReaderTransformText.Text ?? string.Empty;
                start = transform.IndexOf(quote, StringComparison.Ordinal);
                if (start < 0)
                {
                    SetCandidateStatus("引用文本未在当前 Core transform 中找到；未提交。", "error");
                    return;
                }
                if (transform.IndexOf(quote, start + quote.Length, StringComparison.Ordinal) >= 0)
                {
                    SetCandidateStatus("引用文本在当前 transform 中出现多次；请补充更长、更具体的引用。", "error");
                    return;
                }
                end = start + quote.Length;
            }
        }
        if (row is null || string.IsNullOrWhiteSpace(quote) || LoadedTransformId is null || string.IsNullOrWhiteSpace(LoadedRawSha256))
        {
            SetCandidateStatus("请先读取成功的 text transform，并选中或粘贴一段引用文本。", "empty");
            return;
        }
        SourceReaderQuoteBox.Text = quote;
        var body = SourceReaderCandidateBodyBox.Text?.Trim();
        if (string.IsNullOrWhiteSpace(body))
            body = quote.Trim();
        SourceBoundCandidateRequested?.Invoke(this, new SourceBoundCandidateRequestedEventArgs(
            row, body, quote, start, end, LoadedTransformId.Value, LoadedRawSha256));
    }

    public void SetCandidateStatus(string text, string semanticClass)
    {
        SourceReaderCandidateStatusText.Text = text;
        AutomationProperties.SetName(SourceReaderCandidateStatusText, text);
        foreach (var item in new[] { "loading", "empty", "error", "permission", "success", "info" })
            SourceReaderCandidateStatusText.Classes.Set($"status-{item}", string.Equals(item, semanticClass, StringComparison.Ordinal));
    }

    public bool CandidateSubmissionInProgress { get; private set; }

    public void SetCandidateSubmissionInProgress(bool value)
    {
        CandidateSubmissionInProgress = value;
        UpdateCandidateAction();
    }

    private void UpdateCandidateAction()
    {
        CreateSourceBoundCandidateButton.IsEnabled = SelectedRow is not null
            && !CandidateSubmissionInProgress
            && LoadedTransformId is not null
            && !string.IsNullOrWhiteSpace(LoadedRawSha256);
    }

    private void OnRowsKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key != Key.Enter)
            return;
        ReadTransformRequested?.Invoke(this, new SourceReaderRowActionEventArgs(SelectedRow));
        e.Handled = true;
    }

    private void OnRowsDoubleTapped(object? sender, TappedEventArgs e)
    {
        ReadTransformRequested?.Invoke(this, new SourceReaderRowActionEventArgs(SelectedRow));
        e.Handled = true;
    }

    private void OnOpenJobClick(object? sender, RoutedEventArgs e) => OpenJobRequested?.Invoke(this, new SourceReaderRowActionEventArgs(SelectedRow));
    private void OnLibraryLookupClick(object? sender, RoutedEventArgs e) => LibraryLookupRequested?.Invoke(this, new SourceReaderRowActionEventArgs(SelectedRow));
    private void OnCopyProvenanceClick(object? sender, RoutedEventArgs e) => CopyProvenanceRequested?.Invoke(this, new SourceReaderRowActionEventArgs(SelectedRow));
    private void OnCopyCitationClick(object? sender, RoutedEventArgs e) => CopyCitationRequested?.Invoke(this, new SourceReaderRowActionEventArgs(SelectedRow));
    private void OnReturnToLibraryClick(object? sender, RoutedEventArgs e) => ReturnToLibraryRequested?.Invoke(this, EventArgs.Empty);
    private void OnReturnToKnowledgeClick(object? sender, RoutedEventArgs e) => ReturnToKnowledgeRequested?.Invoke(this, EventArgs.Empty);

    private void OnViewSizeChanged(object? sender, SizeChangedEventArgs e)
    {
        var width = e.NewSize.Width;
        var compact = width < StackBreakpoint;
        SourceReaderShellGrid.ColumnDefinitions = compact
            ? new ColumnDefinitions("*")
            : new ColumnDefinitions("220,*,300");
        SourceReaderShellGrid.RowDefinitions = compact
            ? new RowDefinitions("Auto,Auto,Auto")
            : new RowDefinitions("*");
        Grid.SetColumn(SourceReaderOutlineBorder, 0);
        Grid.SetRow(SourceReaderOutlineBorder, 0);
        Grid.SetColumn(SourceReaderMainBorder, compact ? 0 : 1);
        Grid.SetRow(SourceReaderMainBorder, compact ? 1 : 0);
        Grid.SetColumn(SourceReaderChainBorder, compact ? 0 : 2);
        Grid.SetRow(SourceReaderChainBorder, compact ? 2 : 0);
        SourceReaderMainBorder.Margin = compact ? new Avalonia.Thickness(0, 12, 0, 0) : default;
        SourceReaderChainBorder.Margin = compact ? new Avalonia.Thickness(0, 12, 0, 0) : default;

        var narrowActions = width < NarrowActionsBreakpoint;
        SourceReaderReturnActions.Orientation = narrowActions ? Orientation.Vertical : Orientation.Horizontal;
        SourceReaderContextActions.Orientation = narrowActions ? Orientation.Vertical : Orientation.Horizontal;
        SourceReaderLoadGrid.ColumnDefinitions = narrowActions ? new ColumnDefinitions("*") : new ColumnDefinitions("*,Auto");
        SourceReaderLoadGrid.RowDefinitions = narrowActions ? new RowDefinitions("Auto,Auto") : new RowDefinitions("Auto");
        Grid.SetColumn(SourceReaderLoadButton, narrowActions ? 0 : 1);
        Grid.SetRow(SourceReaderLoadButton, narrowActions ? 1 : 0);
    }
}

using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia;
using Avalonia.Animation;
using Avalonia.Automation;
using Avalonia.Controls;
using Avalonia.Controls.Shapes;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Threading;

namespace ArcheAxis.Desktop;

public sealed class MemoryGraphNodeSelectedEventArgs : EventArgs
{
    public string NodeName { get; }

    public MemoryGraphNodeSelectedEventArgs(string nodeName) => NodeName = nodeName;
}

public partial class AaosMemoryGraphView : UserControl
{
    public const int MasterNodeCount = 14;
    private const double CanvasWidth = 560;
    private const double CanvasHeight = 390;
    private const double CenterX = CanvasWidth / 2;
    private const double CenterY = CanvasHeight / 2;
    private const double HitTargetSize = 44;
    private const double NodeButtonWidth = 84;
    private const double NodeRadius = 6;
    private const double CenterRadius = 30;

    private sealed record GraphNodeDefinition(string Label, double X, double Y);
    private readonly record struct GraphEdgeKey(int Source, int Target);

    // Labels and positions are fixed visual scaffolding copied from the B03
    // composition language. They are not Core IDs, learned facts, or relations.
    private static readonly IReadOnlyList<GraphNodeDefinition> MasterNodes =
    [
        new GraphNodeDefinition("AI", 72, 58),
        new GraphNodeDefinition("认知", 200, 44),
        new GraphNodeDefinition("人类", 356, 52),
        new GraphNodeDefinition("学习", 480, 116),
        new GraphNodeDefinition("记忆", 478, 260),
        new GraphNodeDefinition("思考", 382, 340),
        new GraphNodeDefinition("证据", 238, 350),
        new GraphNodeDefinition("来源", 96, 334),
        new GraphNodeDefinition("时间", 48, 226),
        new GraphNodeDefinition("原创", 70, 118),
        new GraphNodeDefinition("工作区", 188, 138),
        new GraphNodeDefinition("捕获", 362, 136),
        new GraphNodeDefinition("复习", 366, 254),
        new GraphNodeDefinition("关系", 204, 268),
    ];

    private static readonly IReadOnlyList<GraphNodeDefinition> B10HomeNodes =
    [
        // The six master nodes are the product's own domain words, so they are shown in the
        // product's language; the diagram stays a static illustration either way.
        new GraphNodeDefinition("证据", 18, 30),
        new GraphNodeDefinition("原文", 18, 72),
        new GraphNodeDefinition("学习", 49, 15),
        new GraphNodeDefinition("记忆", 82, 28),
        new GraphNodeDefinition("工作区", 85, 71),
        new GraphNodeDefinition("复习", 52, 87),
    ];

    // -1 denotes the central Knowledge node. The cycle, center links, and
    // cross chords form a static mesh; they do not encode real graph data.
    private static readonly IReadOnlyList<(int Source, int Target)> MasterEdges =
    [
        (-1, 0), (-1, 2), (-1, 4), (-1, 6), (-1, 8), (-1, 10), (-1, 12), (-1, 13),
        (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8),
        (8, 9), (9, 0), (10, 11), (11, 12), (12, 13), (13, 10),
        (0, 4), (0, 6), (0, 10), (1, 5), (1, 6), (1, 13), (2, 5),
        (2, 7), (2, 11), (3, 6), (3, 8), (3, 11), (4, 8), (4, 9),
        (5, 9), (5, 10), (5, 12), (6, 10), (6, 11), (7, 11), (7, 12),
        (8, 12), (8, 13), (9, 13), (10, 12), (11, 13),
    ];

    private static readonly IReadOnlyList<(int Source, int Target)> B10HomeEdges =
    [
        (-1, 0), (-1, 1), (-1, 2), (-1, 3), (-1, 4), (-1, 5),
    ];

    private readonly List<Button> _nodes = [];
    private readonly List<Line> _edges = [];
    private bool _useB10HomeLayout;
    private IReadOnlyList<GraphNodeDefinition> ActiveNodes => _useB10HomeLayout ? B10HomeNodes : MasterNodes;
    private IReadOnlyList<(int Source, int Target)> ActiveEdges => _useB10HomeLayout ? B10HomeEdges : MasterEdges;
    private Button? _selectedNode;
    private Button? _hoveredNode;
    private Button? _focusedNode;
    private int? _relationFilterIndex;
    private readonly DispatcherTimer _pulseTimer = new() { Interval = TimeSpan.FromMilliseconds(40) };
    private double _motionElapsedSeconds;
    private bool _reducedMotion;
    private bool _motionActive;

    public event EventHandler<MemoryGraphNodeSelectedEventArgs>? NodeSelected;

    public AaosMemoryGraphView()
    {
        InitializeComponent();
        BuildMasterConstellation();
        _pulseTimer.Tick += OnPulseTick;
        ThemePalette.PaletteChanged += OnPaletteChanged;
    }

    public void SetReducedMotion(bool reducedMotion)
    {
        _reducedMotion = reducedMotion;
        foreach (var node in _nodes)
            node.Transitions = reducedMotion ? new Transitions() : null;
        UpdatePulseState();
    }

    public void SetMotionActive(bool active)
    {
        _motionActive = active;
        UpdatePulseState();
    }

    public void SetRelationFilter(string? nodeName)
    {
        _relationFilterIndex = string.IsNullOrWhiteSpace(nodeName)
            ? null
            : IndexOfNode(nodeName.Trim());
        UpdateRelationHighlight();
    }

    public void UseB10HomeLayout()
    {
        if (_useB10HomeLayout)
            return;

        _useB10HomeLayout = true;
        GraphCanvas.Children.Clear();
        _nodes.Clear();
        _edges.Clear();
        _selectedNode = null;
        _hoveredNode = null;
        _focusedNode = null;
        _relationFilterIndex = null;
        CoreKnowledgeLabel.Text = "Knowledge";
        CoreKnowledgeLabel.FontSize = 14;
        AutomationProperties.SetName(this,
            "B10 记忆图谱静态示意：知识中心与证据、原文、学习、记忆、工作区、复习六个母版节点；不代表 Core 数据");
        BuildMasterConstellation();
        ApplyHomeMasterPalette();
        UpdatePulseState();
    }

    private void BuildMasterConstellation()
    {
        foreach (var (source, target) in ActiveEdges)
        {
            var sourceCenter = GetNodeCenter(source);
            var targetCenter = GetNodeCenter(target);
            var direction = targetCenter - sourceCenter;
            var length = Math.Sqrt(direction.X * direction.X + direction.Y * direction.Y);
            if (length <= 0)
                continue;

            var unit = new Vector(direction.X / length, direction.Y / length);
            var startRadius = source == -1 ? CenterRadius : NodeRadius;
            var endRadius = target == -1 ? CenterRadius : NodeRadius;
            var edge = new Line
            {
                StartPoint = sourceCenter + unit * startRadius,
                EndPoint = targetCenter - unit * endRadius,
                Stroke = ThemePalette.ResolveBrush("AaosBorderBrush"),
                StrokeThickness = 1,
                Opacity = 0.52,
                IsHitTestVisible = false,
                Tag = new GraphEdgeKey(source, target),
            };
            GraphCanvas.Children.Insert(0, edge);
            _edges.Add(edge);
        }

        for (var index = 0; index < ActiveNodes.Count; index++)
        {
            var definition = ActiveNodes[index];
            var marker = new Ellipse
            {
                Width = _useB10HomeLayout ? CanvasHeight * 0.1 : NodeRadius * 2,
                Height = _useB10HomeLayout ? CanvasHeight * 0.1 : NodeRadius * 2,
                Margin = _useB10HomeLayout ? new Thickness(0) : new Thickness(0, 0, 5, 0),
                Fill = _useB10HomeLayout ? ThemePalette.ResolveBrush("AaosSurface2Brush") : Brushes.Transparent,
                Stroke = ThemePalette.ResolveBrush("AaosGoldBrush"),
                StrokeThickness = _useB10HomeLayout ? 2 : 1.5,
                VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center,
            };
            var label = new TextBlock
            {
                Text = definition.Label,
                FontSize = _useB10HomeLayout ? 14.5 : 11,
                FontWeight = FontWeight.Medium,
                Foreground = ThemePalette.ResolveBrush("AaosIvoryBrush"),
                VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center,
            };
            Control content;
            if (_useB10HomeLayout)
            {
                content = new Grid
                {
                    Width = NodeButtonWidth,
                    Height = HitTargetSize,
                    Children = { marker, label },
                };
            }
            else
            {
                content = new StackPanel
                {
                    Orientation = Avalonia.Layout.Orientation.Horizontal,
                    HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                    VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center,
                    Children = { marker, label },
                };
            }
            var node = new Button
            {
                Width = NodeButtonWidth,
                MinHeight = HitTargetSize,
                Padding = new Thickness(4, 0),
                Background = Brushes.Transparent,
                BorderBrush = Brushes.Transparent,
                BorderThickness = new Thickness(0),
                CornerRadius = new CornerRadius(22),
                Classes = { "aaos-graph-node" },
                RenderTransformOrigin = new RelativePoint(0.5, 0.5, RelativeUnit.Relative),
                RenderTransform = new ScaleTransform(),
                Tag = index,
                ZIndex = 2,
                Content = content,
            };
            AutomationProperties.SetName(node,
                $"选择{definition.Label}示意节点；静态示意，不代表 Core 条目或关系");
            AutomationProperties.SetHelpText(node,
                "仅强调静态示意网络中的相邻标签；不读取、不筛选 Core 图谱数据。");
            node.Click += OnNodeClick;
            node.PointerEntered += OnNodePointerEntered;
            node.PointerExited += OnNodePointerExited;
            node.GotFocus += OnNodeGotFocus;
            node.LostFocus += OnNodeLostFocus;
            var center = GetNodeCenter(index);
            Canvas.SetLeft(node, center.X - NodeButtonWidth / 2);
            Canvas.SetTop(node, center.Y - HitTargetSize / 2);
            GraphCanvas.Children.Add(node);
            _nodes.Add(node);
        }
    }

    private Point GetNodeCenter(int index)
    {
        if (index == -1)
            return new Point(CenterX, CenterY);

        var node = ActiveNodes[index];
        if (_useB10HomeLayout)
        {
            var scale = CanvasHeight / 100d;
            return new Point(CenterX + (node.X - 50) * scale, CenterY + (node.Y - 50) * scale);
        }
        return new Point(node.X, node.Y);
    }

    private int IndexOfNode(string label)
    {
        for (var index = 0; index < ActiveNodes.Count; index++)
        {
            if (string.Equals(ActiveNodes[index].Label, label, StringComparison.OrdinalIgnoreCase))
                return index;
        }
        return -1;
    }

    private void OnPaletteChanged(object? sender, EventArgs e)
    {
        foreach (var node in _nodes)
        {
            if (node.Content is StackPanel { Children.Count: >= 2 } content
                && content.Children[1] is TextBlock label)
                label.Foreground = ThemePalette.ResolveBrush("AaosIvoryBrush");
            else if (node.Content is Grid { Children.Count: >= 2 } homeContent
                && homeContent.Children[1] is TextBlock homeLabel)
            {
                homeLabel.Foreground = ThemePalette.ResolveBrush("AaosIvoryBrush");
                if (homeContent.Children[0] is Ellipse marker)
                    marker.Fill = ThemePalette.ResolveBrush("AaosSurface2Brush");
            }
        }
        ApplyHomeMasterPalette();
        UpdateRelationHighlight();
    }

    private void ApplyHomeMasterPalette()
    {
        if (!_useB10HomeLayout)
            return;

        if (ThemePalette.ResolveBrush("AaosPrimaryBrush") is SolidColorBrush primary)
        {
            CoreKnowledgeNode.Effect = new DropShadowEffect
            {
                Color = primary.Color,
                BlurRadius = 18,
                OffsetX = 0,
                OffsetY = 0,
            };
        }
    }

    private void UpdatePulseState()
    {
        if (_reducedMotion || !_motionActive || !IsVisible)
        {
            _pulseTimer.Stop();
            _motionElapsedSeconds = 0;
            var transform = (ScaleTransform)CoreKnowledgeNode.RenderTransform!;
            transform.ScaleX = transform.ScaleY = 1;
            CoreKnowledgeNode.Opacity = 1;
            return;
        }

        if (!_pulseTimer.IsEnabled)
            _pulseTimer.Start();
    }

    private void OnPulseTick(object? sender, EventArgs e)
    {
        const double cycleSeconds = 3;
        _motionElapsedSeconds = (_motionElapsedSeconds + _pulseTimer.Interval.TotalSeconds) % cycleSeconds;
        var easedPulse = (1 - Math.Cos(2 * Math.PI * _motionElapsedSeconds / cycleSeconds)) / 2;
        var transform = (ScaleTransform)CoreKnowledgeNode.RenderTransform!;
        transform.ScaleX = transform.ScaleY = 0.985 + 0.03 * easedPulse;
        CoreKnowledgeNode.Opacity = 0.9 + 0.1 * easedPulse;
    }

    private Button? GetActiveNode() => _hoveredNode ?? _focusedNode ?? _selectedNode;

    private void OnNodePointerEntered(object? sender, PointerEventArgs e)
    {
        if (sender is not Button node)
            return;
        _hoveredNode = node;
        SetNodeScale(node, 1.08);
        UpdateRelationHighlight();
    }

    private void OnNodePointerExited(object? sender, PointerEventArgs e)
    {
        if (sender is not Button node)
            return;
        if (ReferenceEquals(_hoveredNode, node))
            _hoveredNode = null;
        SetNodeScale(node, IsActive(node) ? 1.06 : 1);
        UpdateRelationHighlight();
    }

    private void OnNodeGotFocus(object? sender, Avalonia.Input.FocusChangedEventArgs e)
    {
        if (sender is not Button node)
            return;
        _focusedNode = node;
        node.Classes.Set("focus-visible", true);
        SetNodeScale(node, 1.08);
        UpdateRelationHighlight();
    }

    private void OnNodeLostFocus(object? sender, RoutedEventArgs e)
    {
        if (sender is not Button node)
            return;
        node.Classes.Set("focus-visible", false);
        if (ReferenceEquals(_focusedNode, node))
            _focusedNode = null;
        SetNodeScale(node, IsActive(node) ? 1.06 : 1);
        UpdateRelationHighlight();
    }

    private bool IsActive(Button node) => ReferenceEquals(node, _selectedNode)
        || ReferenceEquals(node, _focusedNode)
        || ReferenceEquals(node, _hoveredNode);

    private void UpdateRelationHighlight()
    {
        var activeNode = GetActiveNode();
        var activeIndex = activeNode?.Tag is int index ? index : _relationFilterIndex ?? -1;
        foreach (var edge in _edges)
        {
            var isRelated = activeIndex < 0
                || edge.Tag is GraphEdgeKey key && (key.Source == activeIndex || key.Target == activeIndex);
            edge.Stroke = isRelated && activeIndex >= 0
                ? ThemePalette.ResolveBrush("AaosPrimaryBrush")
                : ThemePalette.ResolveBrush("AaosBorderBrush");
            edge.StrokeThickness = isRelated && activeIndex >= 0 ? 1.7 : 1;
            edge.Opacity = activeIndex < 0 ? 0.52 : isRelated ? 0.92 : 0.15;
        }

        var adjacent = new HashSet<int>();
        if (activeIndex >= 0)
        {
            adjacent.Add(activeIndex);
            foreach (var (source, target) in ActiveEdges)
            {
                if (source == activeIndex && target >= 0)
                    adjacent.Add(target);
                if (target == activeIndex && source >= 0)
                    adjacent.Add(source);
            }
        }

        foreach (var node in _nodes)
            node.Opacity = activeIndex < 0 || node.Tag is int nodeIndex && adjacent.Contains(nodeIndex) ? 1 : 0.26;
    }

    private void OnNodeClick(object? sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: int index } node || index < 0 || index >= ActiveNodes.Count)
            return;

        _selectedNode?.Classes.Set("selected", false);
        _selectedNode = node;
        node.Classes.Set("selected", true);
        SetNodeScale(node, 1.06);
        UpdateRelationHighlight();
        NodeSelected?.Invoke(this,
            new MemoryGraphNodeSelectedEventArgs($"{ActiveNodes[index].Label}示意节点（静态示意，非 Core 条目或关系）"));
    }

    private static void SetNodeScale(Button node, double scale)
    {
        if (node.RenderTransform is ScaleTransform transform)
        {
            transform.ScaleX = scale;
            transform.ScaleY = scale;
        }
    }
}

using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia;
using Avalonia.Automation;
using Avalonia.Controls;
using Avalonia.Controls.Shapes;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Threading;

namespace ArcheAxis.Desktop;

public partial class AaosMemoryMapConstellation : UserControl
{
    public const int MasterNodeCount = 14;
    private static readonly Point KnowledgeCenter = new(260, 260);
    private const double KnowledgeRadius = 35;
    private const double HollowNodeRadius = 17;

    // B05 uses an evenly spaced, label-free radial constellation. The nodes are
    // positional placeholders only; their count and placement are not Core data.
    private static readonly Point[] MasterCenters =
    [
        new(260, 24), new(363, 46), new(445, 113), new(490, 208),
        new(490, 312), new(445, 407), new(363, 474), new(260, 496),
        new(157, 474), new(75, 407), new(30, 312), new(30, 208),
        new(75, 113), new(157, 46),
    ];

    private Button? _selectedNode;
    private Button? _hoveredNode;
    private Button? _focusedNode;
    private readonly DispatcherTimer _motionTimer = new() { Interval = TimeSpan.FromMilliseconds(16) };
    private readonly List<Line> _spokes = [];
    private Button? _motionNode;
    private double _motionStartScale;
    private double _motionTargetScale;
    private DateTimeOffset _motionStartedAt;
    private bool _reducedMotion;

    public event EventHandler<MemoryGraphNodeSelectedEventArgs>? NodeSelected;

    public AaosMemoryMapConstellation()
    {
        InitializeComponent();
        BuildMasterConstellation();
        _motionTimer.Tick += OnMotionTick;
        ThemePalette.PaletteChanged += OnThemePaletteChanged;
    }

    public void SetReducedMotion(bool reducedMotion)
    {
        _reducedMotion = reducedMotion;
        if (!reducedMotion)
            return;
        _motionTimer.Stop();
        _motionNode = null;
        foreach (var node in GraphCanvas.Children.OfType<Button>())
            if (node.RenderTransform is ScaleTransform transform)
                transform.ScaleX = transform.ScaleY = 1;
    }

    private void AnimateNodeScale(Button node, double targetScale)
    {
        if (node.RenderTransform is not ScaleTransform transform)
            return;
        _motionTimer.Stop();
        if (_reducedMotion)
        {
            transform.ScaleX = transform.ScaleY = targetScale;
            return;
        }

        _motionNode = node;
        _motionStartScale = transform.ScaleX;
        _motionTargetScale = targetScale;
        _motionStartedAt = DateTimeOffset.UtcNow;
        _motionTimer.Start();
    }

    private void OnMotionTick(object? sender, EventArgs e)
    {
        if (_motionNode?.RenderTransform is not ScaleTransform transform)
        {
            _motionTimer.Stop();
            return;
        }
        var progress = Math.Clamp((DateTimeOffset.UtcNow - _motionStartedAt).TotalMilliseconds / 180d, 0, 1);
        var eased = 1 - Math.Pow(1 - progress, 3);
        var scale = _motionStartScale + (_motionTargetScale - _motionStartScale) * eased;
        transform.ScaleX = transform.ScaleY = scale;
        if (progress >= 1)
        {
            _motionTimer.Stop();
            _motionNode = null;
        }
    }

    private void BuildMasterConstellation()
    {
        // Match the B05 mother composition: one knowledge center and fourteen
        // hollow radial markers. These lines are visual scaffolding, not Core data.
        for (var index = 0; index < MasterNodeCount; index++)
        {
            var endpoint = MasterCenters[index];
            var dx = endpoint.X - KnowledgeCenter.X;
            var dy = endpoint.Y - KnowledgeCenter.Y;
            var length = Math.Sqrt(dx * dx + dy * dy);
            var unitX = dx / length;
            var unitY = dy / length;
            var start = new Point(KnowledgeCenter.X + unitX * KnowledgeRadius, KnowledgeCenter.Y + unitY * KnowledgeRadius);
            var end = new Point(endpoint.X - unitX * HollowNodeRadius, endpoint.Y - unitY * HollowNodeRadius);
            _spokes.Add(AddDecorativeEdge(start, end, 0.78, 1.15));
        }

        for (var index = 0; index < MasterNodeCount; index++)
        {
            var center = MasterCenters[index];
            var node = new Button
            {
                Width = 36,
                Height = 36,
                Padding = new Thickness(0),
                Classes = { "aaos-graph-node" },
                CornerRadius = new CornerRadius(18),
                BorderThickness = new Thickness(0),
                Background = Brushes.Transparent,
                Tag = index,
                ZIndex = 2,
                RenderTransformOrigin = new RelativePoint(0.5, 0.5, RelativeUnit.Relative),
                RenderTransform = new ScaleTransform(1, 1),
            };
            node.BorderBrush = Brushes.Transparent;
            AutomationProperties.SetName(node, $"选择第 {index + 1} 个空心示意节点；不代表 Core 中的知识条目或关系");
            AutomationProperties.SetHelpText(node, "只强调母版示意连线，不表示真实图谱数据。");
            node.Content = new Ellipse
            {
                Width = 34,
                Height = 34,
                HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center,
            };
            node.Click += OnNodeClick;
            node.PointerEntered += OnNodePointerEntered;
            node.PointerExited += OnNodePointerExited;
            node.GotFocus += OnNodeGotFocus;
            node.LostFocus += OnNodeLostFocus;
            Canvas.SetLeft(node, center.X - node.Width / 2);
            Canvas.SetTop(node, center.Y - node.Height / 2);
            GraphCanvas.Children.Add(node);
        }

        var centerNode = new Border
        {
            Width = 70,
            Height = 70,
            CornerRadius = new CornerRadius(35),
            Background = ThemePalette.ResolveBrush("AaosPrimaryBrush"),
            BorderBrush = ThemePalette.ResolveBrush("AaosPrimaryBrush"),
            BorderThickness = new Thickness(1),
            ZIndex = 3,
            Child = new TextBlock
            {
                Text = "知识",
                FontSize = 13,
                FontWeight = FontWeight.SemiBold,
                Foreground = ThemePalette.ResolveBrush("AaosPrimaryTextBrush"),
                HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center,
            },
        };
        Canvas.SetLeft(centerNode, 225);
        Canvas.SetTop(centerNode, 225);
        GraphCanvas.Children.Add(centerNode);
    }

    private Line AddDecorativeEdge(Point start, Point end, double opacity, double thickness)
    {
        var line = new Line
        {
            StartPoint = start,
            EndPoint = end,
            StrokeThickness = thickness,
            Opacity = opacity,
            IsHitTestVisible = false,
        };
        line.Stroke = ThemePalette.ResolveBrush("AaosBorderBrush");
        GraphCanvas.Children.Insert(0, line);
        return line;
    }

    private void OnThemePaletteChanged(object? sender, EventArgs e)
    {
        foreach (var child in GraphCanvas.Children)
        {
            if (child is Line line)
                line.Stroke = ReferenceEquals(line, GetActiveSpoke())
                    ? ThemePalette.ResolveBrush("AaosPrimaryBrush")
                    : ThemePalette.ResolveBrush("AaosBorderBrush");
            else if (child is Border { Child: TextBlock centerLabel } center)
            {
                center.Background = ThemePalette.ResolveBrush("AaosPrimaryBrush");
                center.BorderBrush = ThemePalette.ResolveBrush("AaosPrimaryBrush");
                centerLabel.Foreground = ThemePalette.ResolveBrush("AaosPrimaryTextBrush");
            }
        }
        UpdateInteractionEmphasis();
    }

    private void OnNodePointerEntered(object? sender, Avalonia.Input.PointerEventArgs e)
    {
        if (sender is not Button node)
            return;
        _hoveredNode = node;
        AnimateNodeScale(node, 1.12);
        UpdateInteractionEmphasis();
    }

    private void OnNodePointerExited(object? sender, Avalonia.Input.PointerEventArgs e)
    {
        if (sender is not Button node)
            return;
        if (ReferenceEquals(_hoveredNode, node))
            _hoveredNode = null;
        AnimateNodeScale(node, IsActive(node) ? 1.08 : 1.0);
        UpdateInteractionEmphasis();
    }

    private void OnNodeGotFocus(object? sender, Avalonia.Input.FocusChangedEventArgs e)
    {
        if (sender is not Button node)
            return;
        _focusedNode = node;
        node.Classes.Set("focus-visible", true);
        AnimateNodeScale(node, 1.12);
        UpdateInteractionEmphasis();
    }

    private void OnNodeLostFocus(object? sender, RoutedEventArgs e)
    {
        if (sender is not Button node)
            return;
        node.Classes.Set("focus-visible", false);
        if (ReferenceEquals(_focusedNode, node))
            _focusedNode = null;
        AnimateNodeScale(node, IsActive(node) ? 1.08 : 1.0);
        UpdateInteractionEmphasis();
    }

    private Button? GetActiveNode() => _hoveredNode ?? _focusedNode ?? _selectedNode;

    private Line? GetActiveSpoke()
    {
        if (GetActiveNode()?.Tag is not int index || index < 0 || index >= _spokes.Count)
            return null;
        return _spokes[index];
    }

    private bool IsActive(Button node) => ReferenceEquals(node, _selectedNode)
        || ReferenceEquals(node, _focusedNode)
        || ReferenceEquals(node, _hoveredNode);

    private void UpdateInteractionEmphasis()
    {
        var activeNode = GetActiveNode();
        var activeSpoke = GetActiveSpoke();
        foreach (var spoke in _spokes)
        {
            var isActive = ReferenceEquals(spoke, activeSpoke);
            spoke.Stroke = isActive
                ? ThemePalette.ResolveBrush("AaosPrimaryBrush")
                : ThemePalette.ResolveBrush("AaosBorderBrush");
            spoke.StrokeThickness = isActive ? 1.8 : 1.15;
            spoke.Opacity = activeNode is null ? 0.78 : isActive ? 1 : 0.2;
        }

        foreach (var node in GraphCanvas.Children.OfType<Button>())
            node.Opacity = activeNode is null || ReferenceEquals(node, activeNode) ? 1 : 0.55;
    }

    private void OnNodeClick(object? sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: int index } selectedNode)
            return;

        _selectedNode?.Classes.Set("selected", false);
        _selectedNode = selectedNode;
        _selectedNode.Classes.Set("selected", true);
        AnimateNodeScale(_selectedNode, 1.08);
        UpdateInteractionEmphasis();
        NodeSelected?.Invoke(this, new MemoryGraphNodeSelectedEventArgs($"第 {index + 1} 个空心示意节点（非 Core 数据）"));
    }
}

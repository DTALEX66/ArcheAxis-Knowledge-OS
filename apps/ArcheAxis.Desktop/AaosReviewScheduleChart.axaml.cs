using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Avalonia;
using Avalonia.Animation;
using Avalonia.Automation;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Avalonia.Threading;

namespace ArcheAxis.Desktop;

/// <summary>A single day and count returned by the real review schedule projection.</summary>
public sealed record ReviewScheduleDay(DateOnly Day, int DueCount);

public partial class AaosReviewScheduleChart : UserControl
{
    public static readonly StyledProperty<IReadOnlyList<ReviewScheduleDay>?> ScheduleProperty =
        AvaloniaProperty.Register<AaosReviewScheduleChart, IReadOnlyList<ReviewScheduleDay>?>(nameof(Schedule));

    private const int ForecastDays = 7;
    private const double MinimumPlotHeight = 190;
    private readonly bool _reducedMotion = string.Equals(
        Environment.GetEnvironmentVariable("AAOS_REDUCED_MOTION"), "1", StringComparison.OrdinalIgnoreCase);

    public IReadOnlyList<ReviewScheduleDay>? Schedule
    {
        get => GetValue(ScheduleProperty);
        set => SetValue(ScheduleProperty, value);
    }

    public AaosReviewScheduleChart()
    {
        InitializeComponent();
        UpdateTimelineAxis();
        ScheduleBarsCanvas.SizeChanged += (_, _) => RenderScheduleBars();
        RefreshSchedule();
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);
        if (change.Property == ScheduleProperty)
            RefreshSchedule();
    }

    protected override void OnAttachedToVisualTree(VisualTreeAttachmentEventArgs e)
    {
        base.OnAttachedToVisualTree(e);
        ThemePalette.PaletteChanged += OnPaletteChanged;
        RefreshSchedule();
    }

    protected override void OnDetachedFromVisualTree(VisualTreeAttachmentEventArgs e)
    {
        ThemePalette.PaletteChanged -= OnPaletteChanged;
        base.OnDetachedFromVisualTree(e);
    }

    private void OnPaletteChanged(object? sender, EventArgs e) => RenderScheduleBars();

    private void RefreshSchedule()
    {
        UpdateTimelineAxis();
        var points = Schedule;
        if (points is null || points.Count == 0)
        {
            ShowEmptyState("Core 未提供未来复习数量；收到真实排程后在此显示。", "复习排程图表；尚未收到 Core 排程数据。");
            return;
        }

        if (!TryValidateProjection(points, out var validationMessage))
        {
            ShowEmptyState(validationMessage, "复习排程图表；Core 排程数据无效，未绘制数据。");
            return;
        }

        EmptyState.IsVisible = false;
        ScheduleBarsCanvas.IsVisible = true;
        CoreStatusText.Text = "CORE · 已提供";
        AutomationProperties.SetName(CoreStatusTag, "数据来源 Core；排程数据已提供");
        AutomationProperties.SetName(this, "复习排程图表；柱值来自 Core 返回的真实每日复习排程数量。");
        RenderScheduleBars();
    }

    private void UpdateTimelineAxis()
    {
        var today = DateOnly.FromDateTime(DateTime.Now);
        var labels = new[] { AxisDay0, AxisDay1, AxisDay2, AxisDay3, AxisDay4, AxisDay5, AxisDay6 };
        for (var dayOffset = 0; dayOffset < labels.Length; dayOffset++)
        {
            var date = today.AddDays(dayOffset);
            labels[dayOffset].Text = dayOffset == 0
                ? $"今天\n{date.ToString("M/d", CultureInfo.CurrentCulture)}"
                : $"{date.ToString("ddd", CultureInfo.CurrentCulture)}\n{date.ToString("M/d", CultureInfo.CurrentCulture)}";
            AutomationProperties.SetName(labels[dayOffset], date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
        }
    }

    private static bool TryValidateProjection(IReadOnlyList<ReviewScheduleDay> points, out string message)
    {
        var today = DateOnly.FromDateTime(DateTime.Now);
        var dates = new HashSet<DateOnly>();
        foreach (var point in points)
        {
            var offset = point.Day.DayNumber - today.DayNumber;
            if (point.DueCount < 0 || offset is < 0 or >= ForecastDays || !dates.Add(point.Day))
            {
                message = "Core 排程数据无效或超出未来 7 天范围；未绘制数据。";
                return false;
            }
        }

        if (points.Count > ForecastDays)
        {
            message = "Core 排程数据超过未来 7 天范围；未绘制数据。";
            return false;
        }

        message = string.Empty;
        return true;
    }

    private void ShowEmptyState(string description, string accessibleName)
    {
        ScheduleBarsCanvas.Children.Clear();
        ScheduleBarsCanvas.IsVisible = false;
        EmptyDescriptionText.Text = description;
        EmptyState.IsVisible = true;
        CoreStatusText.Text = "CORE · 未提供";
        AutomationProperties.SetName(CoreStatusTag, "数据来源 Core；排程数据未提供或无效");
        AutomationProperties.SetName(this, accessibleName);
    }

    private void RenderScheduleBars()
    {
        if (!ScheduleBarsCanvas.IsVisible || Schedule is not { Count: > 0 } points)
            return;

        var width = ScheduleBarsCanvas.Bounds.Width;
        var height = Math.Max(ScheduleBarsCanvas.Bounds.Height, MinimumPlotHeight);
        if (width <= 0)
            return;

        ScheduleBarsCanvas.Children.Clear();
        var maximum = points.Max(point => point.DueCount);
        var maximumBarHeight = Math.Max(0, height - 30);
        var cellWidth = width / ForecastDays;
        var barWidth = Math.Clamp(cellWidth * 0.36, 5, 40);
        var today = DateOnly.FromDateTime(DateTime.Now);
        var barBrush = ThemePalette.ResolveBrush("AaosPrimaryBrush");
        var valueBrush = ThemePalette.ResolveBrush("AaosIvoryBrush");
        var pointsByOffset = points.ToDictionary(point => point.Day.DayNumber - today.DayNumber);

        for (var dayOffset = 0; dayOffset < ForecastDays; dayOffset++)
        {
            var centerX = (dayOffset + 0.5) * cellWidth;
            if (!pointsByOffset.TryGetValue(dayOffset, out var point))
            {
                var missingLabel = new TextBlock
                {
                    Text = "—",
                    Width = cellWidth,
                    TextAlignment = TextAlignment.Center,
                    FontSize = 10,
                    Foreground = ThemePalette.ResolveBrush("AaosMutedBrush"),
                };
                ToolTip.SetTip(missingLabel, "Core 未返回这一天的排程数量");
                AutomationProperties.SetName(missingLabel, $"{today.AddDays(dayOffset):yyyy-MM-dd}：Core 未返回排程数量");
                Canvas.SetLeft(missingLabel, centerX - cellWidth / 2);
                Canvas.SetTop(missingLabel, height - 16);
                ScheduleBarsCanvas.Children.Add(missingLabel);
                continue;
            }

            var barHeight = maximum == 0
                ? 0
                : Math.Max(2, point.DueCount / (double)maximum * maximumBarHeight);
            var valueLabel = new TextBlock
            {
                Text = point.DueCount.ToString(CultureInfo.InvariantCulture),
                Width = cellWidth,
                TextAlignment = TextAlignment.Center,
                FontSize = 10,
                FontWeight = FontWeight.SemiBold,
                Foreground = valueBrush,
            };
            Canvas.SetLeft(valueLabel, centerX - cellWidth / 2);
            Canvas.SetTop(valueLabel, Math.Max(0, height - barHeight - 18));
            ScheduleBarsCanvas.Children.Add(valueLabel);

            var bar = new Border
            {
                Width = barWidth,
                Height = point.DueCount == 0 ? 2 : barHeight,
                CornerRadius = new CornerRadius(4, 4, 1, 1),
                Background = barBrush,
                BorderBrush = Brushes.Transparent,
                BorderThickness = new Thickness(0),
                Opacity = _reducedMotion ? 0.96 : 0,
                RenderTransformOrigin = new RelativePoint(0.5, 0.5, RelativeUnit.Relative),
                RenderTransform = new ScaleTransform(),
                Transitions = new Transitions
                {
                    new DoubleTransition
                    {
                        Property = Visual.OpacityProperty,
                        Duration = TimeSpan.FromMilliseconds(180),
                    },
                },
            };
            Canvas.SetLeft(bar, centerX - barWidth / 2);
            Canvas.SetTop(bar, height - bar.Height);
            ScheduleBarsCanvas.Children.Add(bar);
            if (!_reducedMotion)
                Dispatcher.UIThread.Post(() => bar.Opacity = 0.96, DispatcherPriority.Render);

            var hitTarget = new Border
            {
                Width = cellWidth,
                Height = height,
                Background = Brushes.Transparent,
                Focusable = true,
                Cursor = new Cursor(StandardCursorType.Hand),
            };
            var accessibleName = $"{point.Day:yyyy-MM-dd}：{point.DueCount} 张到期复习卡片";
            ToolTip.SetTip(hitTarget, $"{point.Day:yyyy-MM-dd} · {point.DueCount} 张");
            AutomationProperties.SetName(hitTarget, accessibleName);
            hitTarget.PointerEntered += (_, _) => SetBarEmphasis(bar, true);
            hitTarget.PointerExited += (_, _) => SetBarEmphasis(bar, hitTarget.IsFocused);
            hitTarget.GotFocus += (_, _) => SetBarEmphasis(bar, true);
            hitTarget.LostFocus += (_, _) => SetBarEmphasis(bar, false);
            Canvas.SetLeft(hitTarget, dayOffset * cellWidth);
            Canvas.SetTop(hitTarget, 0);
            ScheduleBarsCanvas.Children.Add(hitTarget);
        }
    }

    private static void SetBarEmphasis(Border bar, bool emphasized)
    {
        bar.Opacity = emphasized ? 1 : 0.96;
        if (bar.RenderTransform is ScaleTransform scale)
        {
            scale.ScaleX = emphasized ? 1.08 : 1;
            scale.ScaleY = emphasized ? 1.035 : 1;
        }

        bar.BorderBrush = emphasized ? ThemePalette.ResolveBrush("AaosIvoryBrush") : Brushes.Transparent;
        bar.BorderThickness = emphasized ? new Thickness(1) : new Thickness(0);
        bar.Effect = emphasized && ThemePalette.ResolveBrush("AaosPrimaryBrush") is SolidColorBrush primary
            ? new DropShadowEffect
            {
                Color = primary.Color,
                BlurRadius = 14,
                OffsetX = 0,
                OffsetY = 0,
            }
            : null;
    }
}

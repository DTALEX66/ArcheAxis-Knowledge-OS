using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Threading;
using Avalonia.VisualTree;
using System;

namespace ArcheAxis.Desktop;

/// <summary>Theme-aware orbital light behind the application shell.</summary>
internal sealed class AaosBackdrop : Control
{
    private const double GridSpacing = 32;
    // Ambient light moves slowly; a high-frequency full-window redraw adds no useful detail.
    private readonly DispatcherTimer _animationTimer = new() { Interval = TimeSpan.FromMilliseconds(250) };
    private readonly bool _reducedMotion;
    private Window? _hostWindow;
    private double _animationPhase;

    public AaosBackdrop()
    {
        _reducedMotion = string.Equals(Environment.GetEnvironmentVariable("AAOS_REDUCED_MOTION"), "1", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Environment.GetEnvironmentVariable("AAOS_REDUCED_MOTION"), "true", StringComparison.OrdinalIgnoreCase);
        _animationTimer.Tick += OnAnimationTick;
        ThemePalette.PaletteChanged += OnPaletteChanged;
    }

    protected override void OnAttachedToVisualTree(VisualTreeAttachmentEventArgs e)
    {
        base.OnAttachedToVisualTree(e);
        _hostWindow = TopLevel.GetTopLevel(this) as Window;
        if (_hostWindow is not null)
        {
            _hostWindow.Activated += OnWindowActivityChanged;
            _hostWindow.Deactivated += OnWindowActivityChanged;
        }
        UpdateAnimationState();
    }

    protected override void OnDetachedFromVisualTree(VisualTreeAttachmentEventArgs e)
    {
        _animationTimer.Stop();
        if (_hostWindow is not null)
        {
            _hostWindow.Activated -= OnWindowActivityChanged;
            _hostWindow.Deactivated -= OnWindowActivityChanged;
            _hostWindow = null;
        }
        base.OnDetachedFromVisualTree(e);
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);
        if (change.Property == IsVisibleProperty)
            UpdateAnimationState();
    }

    public override void Render(DrawingContext context)
    {
        base.Render(context);

        var width = Bounds.Width;
        var height = Bounds.Height;
        if (width <= 0 || height <= 0)
            return;

        using (context.PushOpacity(0.45))
        {
            var phase = _reducedMotion ? 0 : _animationPhase;
            DrawAmbient(context, "AaosAmbientPrimaryBrush", new Point(width * 0.08, height * 0.08), 360, phase);
            DrawAmbient(context, "AaosAmbientSecondaryBrush", new Point(width * 0.92, height * 0.18), 320, phase - 2 * Math.PI / 3);
            DrawAmbient(context, "AaosAmbientTertiaryBrush", new Point(width * 0.48, height * 0.98), 280, phase - 7 * Math.PI / 6);
        }

        // The orbit is a restrained brand accent, kept away from the reading center.
        var orbitCenter = new Point(width * 0.94, height * 0.10);
        var orbitRadius = Math.Min(width, height) * 0.17;
        var orbitBrush = ThemePalette.ResolveBrush("AaosGridBrush");
        using (context.PushOpacity(0.30))
        {
            context.DrawEllipse(null, new Pen(orbitBrush, 1), orbitCenter, orbitRadius, orbitRadius * 0.43);
            context.DrawEllipse(null, new Pen(orbitBrush, 0.8), orbitCenter, orbitRadius * 0.72, orbitRadius * 0.31);
        }
        // A fixed star keeps the low-frequency ambient timer from looking like stepped motion.
        var starPoint = new Point(orbitCenter.X + orbitRadius, orbitCenter.Y);
        using (context.PushOpacity(0.55))
            context.DrawEllipse(ThemePalette.ResolveBrush("AaosAmbientPrimaryBrush"), null, starPoint, 3, 3);

        var maskRadius = Math.Max(width, height) * 0.95 / 2;
        var gridMask = new RadialGradientBrush
        {
            Center = new RelativePoint(width / 2, height / 2, RelativeUnit.Absolute),
            GradientOrigin = new RelativePoint(width / 2, height / 2, RelativeUnit.Absolute),
            RadiusX = new RelativeScalar(maskRadius, RelativeUnit.Absolute),
            RadiusY = new RelativeScalar(maskRadius, RelativeUnit.Absolute),
            GradientStops =
            {
                new GradientStop(Colors.Black, 0),
                new GradientStop(Colors.Black, 0.45 / 0.95),
                new GradientStop(Colors.Transparent, 1),
            },
        };
        using (context.PushOpacityMask(gridMask, new Rect(0, 0, width, height)))
        {
            var gridPen = new Pen(ThemePalette.ResolveBrush("AaosGridBrush"), 1);
            for (var x = 0d; x <= width; x += GridSpacing)
                context.DrawLine(gridPen, new Point(x, 0), new Point(x, height));
            for (var y = 0d; y <= height; y += GridSpacing)
                context.DrawLine(gridPen, new Point(0, y), new Point(width, y));
        }
    }

    private static void DrawAmbient(DrawingContext context, string resourceKey, Point origin, double radius, double phase)
    {
        var travel = (1 - Math.Cos(phase)) / 2;
        var scale = 1 + 0.06 * travel;
        var center = new Point(origin.X + 12 * travel, origin.Y + 20 * travel);
        context.DrawEllipse(CreateGlow(resourceKey), null, center, radius * scale, radius * scale);
    }

    private static RadialGradientBrush CreateGlow(string resourceKey)
    {
        var color = ThemePalette.ResolveBrush(resourceKey) is ISolidColorBrush solid
            ? solid.Color
            : Colors.Transparent;
        var transparent = Color.FromArgb(0, color.R, color.G, color.B);
        return new RadialGradientBrush
        {
            Center = new RelativePoint(0.5, 0.5, RelativeUnit.Relative),
            GradientOrigin = new RelativePoint(0.5, 0.5, RelativeUnit.Relative),
            RadiusX = new RelativeScalar(0.5, RelativeUnit.Relative),
            RadiusY = new RelativeScalar(0.5, RelativeUnit.Relative),
            GradientStops =
            {
                new GradientStop(color, 0),
                new GradientStop(Color.FromArgb((byte)(color.A * 0.6), color.R, color.G, color.B), 0.58),
                new GradientStop(transparent, 1),
            },
        };
    }

    private void OnPaletteChanged(object? sender, System.EventArgs e) => InvalidateVisual();

    private void OnWindowActivityChanged(object? sender, EventArgs e) => UpdateAnimationState();

    private void UpdateAnimationState()
    {
        if (_reducedMotion || !IsVisible || _hostWindow is null || !_hostWindow.IsActive)
            _animationTimer.Stop();
        else
            _animationTimer.Start();
    }

    private void OnAnimationTick(object? sender, EventArgs e)
    {
        _animationPhase = (_animationPhase + Math.PI * 2 * _animationTimer.Interval.TotalSeconds / 12) % (Math.PI * 2);
        InvalidateVisual();
    }
}

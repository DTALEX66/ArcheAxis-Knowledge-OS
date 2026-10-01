using System;
using System.Diagnostics;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Threading;
using Avalonia.VisualTree;

namespace ArcheAxis.Desktop;

/// <summary>Small B03 orbit overlay for the existing theme-aware Home planet artwork.</summary>
public partial class AaosHomeHeroOrbit : UserControl
{
    private static readonly TimeSpan OrbitDuration = TimeSpan.FromSeconds(12);
    private readonly DispatcherTimer OrbitTimer = new() { Interval = TimeSpan.FromMilliseconds(80) };
    private readonly Stopwatch _clock = new();
    private readonly bool _environmentReducedMotion;
    private bool _reducedMotion;
    private bool _isAttached;
    private double _centerX;
    private double _centerY;
    private double _radiusX;
    private double _radiusY;

    public AaosHomeHeroOrbit()
    {
        InitializeComponent();
        _environmentReducedMotion = string.Equals(Environment.GetEnvironmentVariable("AAOS_REDUCED_MOTION"), "1", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Environment.GetEnvironmentVariable("AAOS_REDUCED_MOTION"), "true", StringComparison.OrdinalIgnoreCase);
        OrbitTimer.Tick += OnOrbitTick;
        SizeChanged += (_, _) => UpdateGeometry();
    }

    public void SetReducedMotion(bool reducedMotion)
    {
        _reducedMotion = reducedMotion;
        UpdateMotionState();
    }

    protected override void OnAttachedToVisualTree(VisualTreeAttachmentEventArgs e)
    {
        base.OnAttachedToVisualTree(e);
        _isAttached = true;
        UpdateGeometry();
        UpdateMotionState();
    }

    protected override void OnDetachedFromVisualTree(VisualTreeAttachmentEventArgs e)
    {
        _isAttached = false;
        StopAndReset();
        base.OnDetachedFromVisualTree(e);
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);
        if (change.Property == IsVisibleProperty)
            UpdateMotionState();
    }

    private void UpdateMotionState()
    {
        if (!_isAttached || !IsVisible || _environmentReducedMotion || _reducedMotion)
        {
            StopAndReset();
            return;
        }

        if (!OrbitTimer.IsEnabled)
        {
            _clock.Restart();
            OrbitTimer.Start();
        }
    }

    private void UpdateGeometry()
    {
        _centerX = Bounds.Width * 0.80;
        _centerY = Bounds.Height * 0.49;
        _radiusX = Math.Min(110, Bounds.Width * 0.17);
        _radiusY = Math.Min(48, Bounds.Height * 0.27);
        OrbitTrack.Width = _radiusX * 2;
        OrbitTrack.Height = _radiusY * 2;
        Canvas.SetLeft(OrbitTrack, _centerX - _radiusX);
        Canvas.SetTop(OrbitTrack, _centerY - _radiusY);
        PositionSatellite();
    }

    private void OnOrbitTick(object? sender, EventArgs e) => PositionSatellite();

    private void PositionSatellite()
    {
        var phase = _clock.IsRunning ? _clock.Elapsed.TotalSeconds % OrbitDuration.TotalSeconds / OrbitDuration.TotalSeconds : 0;
        var angle = phase * 2 * Math.PI;
        Canvas.SetLeft(OrbitSatellite, _centerX + Math.Cos(angle) * _radiusX - OrbitSatellite.Width / 2);
        Canvas.SetTop(OrbitSatellite, _centerY + Math.Sin(angle) * _radiusY - OrbitSatellite.Height / 2);
    }

    private void StopAndReset()
    {
        OrbitTimer.Stop();
        _clock.Reset();
        PositionSatellite();
    }
}

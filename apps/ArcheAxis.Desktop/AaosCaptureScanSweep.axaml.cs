using System;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Threading;
using Avalonia.VisualTree;
using System.Diagnostics;

namespace ArcheAxis.Desktop;

public partial class AaosCaptureScanSweep : UserControl
{
    private static readonly TimeSpan SweepDuration = TimeSpan.FromSeconds(2.4);
    private readonly DispatcherTimer SweepTimer = new() { Interval = TimeSpan.FromMilliseconds(16) };
    private readonly Stopwatch _clock = new();
    private TranslateTransform _translation = null!;
    private bool _isAttached;
    private bool _sweepActive;
    private bool _reducedMotion;

    public AaosCaptureScanSweep()
    {
        InitializeComponent();
        _translation = (TranslateTransform)ScanBar.RenderTransform!;
        SweepTimer.Tick += OnSweepTick;
        SizeChanged += (_, _) => UpdateSweepPosition();
    }

    public void SetReducedMotion(bool reducedMotion)
    {
        _reducedMotion = reducedMotion;
        IsVisible = _sweepActive && !_reducedMotion;
        UpdateSweepState();
    }

    public void SetSweepActive(bool active)
    {
        _sweepActive = active;
        IsVisible = _sweepActive && !_reducedMotion;
        UpdateSweepState();
    }

    protected override void OnAttachedToVisualTree(VisualTreeAttachmentEventArgs e)
    {
        base.OnAttachedToVisualTree(e);
        _isAttached = true;
        UpdateSweepState();
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
            UpdateSweepState();
    }

    private void UpdateSweepState()
    {
        if (!_isAttached || !IsVisible || !_sweepActive || _reducedMotion)
        {
            StopAndReset();
            return;
        }

        if (!SweepTimer.IsEnabled)
        {
            _clock.Restart();
            SweepTimer.Start();
        }
    }

    private void OnSweepTick(object? sender, EventArgs e)
    {
        const double start = -1.2;
        const double travel = 5.4;
        var phase = (_clock.Elapsed.TotalSeconds % SweepDuration.TotalSeconds) / SweepDuration.TotalSeconds;
        _translation.Y = (start + (travel * phase)) * Bounds.Height;
    }

    private void UpdateSweepPosition()
    {
        if (!SweepTimer.IsEnabled)
            ResetSweep();
    }

    private void StopAndReset()
    {
        SweepTimer.Stop();
        _clock.Reset();
        ResetSweep();
    }

    private void ResetSweep()
    {
        const double start = -1.2;
        _translation.Y = start * Bounds.Height;
    }
}

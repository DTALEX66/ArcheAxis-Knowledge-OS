using System;
using Avalonia;
using Avalonia.Media;
using Avalonia.Styling;
using System.Collections.Generic;

namespace ArcheAxis.Desktop;

/// <summary>Applies the two user-selectable AAOS palettes.</summary>
internal static class ThemePalette
{
    internal const string Monochrome = "黑白深色";
    internal const string Aurora = "Aurora Teal";
    internal static event EventHandler? PaletteChanged;
    public static void Apply(string palette)
    {
        var colors = palette == Monochrome ? MonochromeColors : AuroraColors;
        var resources = Application.Current?.Resources;
        if (resources is null)
            return;

        foreach (var (key, value) in colors)
            resources[key] = new SolidColorBrush(Color.Parse(value));

        resources["AaosGraphGlowColor"] = Color.Parse(palette == Aurora ? "#662EC4B6" : "#66E1E4E6");
        resources["AaosBrandMarkGlowEffect"] = new DropShadowEffect
        {
            Color = Color.Parse(palette == Aurora ? "#66F4D08B" : "#66E1E4E6"),
            BlurRadius = 30,
            OffsetX = 0,
            OffsetY = 10,
        };

        resources["AaosPrimaryGradientBrush"] = Gradient(colors["AaosPrimaryBrush"], colors["AaosPrimaryGradientEnd"]);
        resources["AaosBrandMarkBrush"] = BrandGradient(palette, colors);
        resources["AaosNavActiveBrush"] = Gradient(colors["AaosNavActiveStart"], colors["AaosNavActiveEnd"]);
        resources["AaosAmbientGlowBrush"] = Gradient(colors["AaosAmbientStart"], colors["AaosAmbientMiddle"], colors["AaosAmbientEnd"]);
        PaletteChanged?.Invoke(null, EventArgs.Empty);
    }

    internal static IBrush ResolveBrush(string key)
    {
        if (Application.Current is { } application
            && application.TryGetResource(key, ThemeVariant.Default, out var resource)
            && resource is IBrush brush)
            return brush;

        return Brushes.Transparent;
    }

    private static LinearGradientBrush BrandGradient(string palette, IReadOnlyDictionary<string, string> colors)
    {
        var start = palette == Aurora ? colors["AaosGoldBrush"] : "#E2E5E7";
        var end = palette == Aurora ? colors["AaosPrimaryBrush"] : "#ADB4B8";
        return Gradient(start, end);
    }

    private static LinearGradientBrush Gradient(params string[] stops)
    {
        var brush = new LinearGradientBrush
        {
            StartPoint = new RelativePoint(0, 0, RelativeUnit.Relative),
            EndPoint = new RelativePoint(1, 1, RelativeUnit.Relative),
        };
        for (var index = 0; index < stops.Length; index++)
            brush.GradientStops.Add(new GradientStop(Color.Parse(stops[index]), (double)index / (stops.Length - 1)));
        return brush;
    }

    private static readonly IReadOnlyDictionary<string, string> MonochromeColors = new Dictionary<string, string>
    {
        ["AaosBackgroundBrush"] = "#080A0C",
        ["AaosSidebarBrush"] = "#101316",
        ["AaosSurfaceBrush"] = "#171A1D",
        ["AaosSurface2Brush"] = "#202428",
        ["AaosBorderBrush"] = "#3B4146",
        ["AaosPrimaryBrush"] = "#E1E4E6",
        ["AaosPrimaryTextBrush"] = "#101214",
        ["AaosGoldBrush"] = "#B6AA8D",
        ["AaosSuccessBrush"] = "#83A292",
        ["AaosErrorBrush"] = "#C78484",
        ["AaosInfoBrush"] = "#A5ADB3",
        ["AaosWarningBrush"] = "#B6AA8D",
        ["AaosApprovalBrush"] = "#A4B294",
        ["AaosDisabledBrush"] = "#72797E",
        ["AaosReviewBrush"] = "#B6AA8D",
        ["AaosIvoryBrush"] = "#F1F2F3",
        ["AaosMutedBrush"] = "#A5ADB3",
        ["AaosOverlayBrush"] = "#99080A0C",
        ["AaosPrimaryGradientEnd"] = "#CFD3D6",
        ["AaosBrandMarkEnd"] = "#A9B0B4",
        ["AaosGridBrush"] = "#0DFFFFFF",
        ["AaosAmbientPrimaryBrush"] = "#66E1E4E6",
        ["AaosAmbientSecondaryBrush"] = "#55B6AA8D",
        ["AaosAmbientTertiaryBrush"] = "#40E1E4E6",
        ["AaosNavActiveStart"] = "#292E32",
        ["AaosNavActiveEnd"] = "#202428",
        ["AaosAmbientStart"] = "#C5C9CC",
        ["AaosAmbientMiddle"] = "#747B80",
        ["AaosAmbientEnd"] = "#171A1D",
    };

    private static readonly IReadOnlyDictionary<string, string> AuroraColors = new Dictionary<string, string>
    {
        ["AaosBackgroundBrush"] = "#081020",
        ["AaosSidebarBrush"] = "#0C1728",
        ["AaosSurfaceBrush"] = "#101D2E",
        ["AaosSurface2Brush"] = "#1A2233",
        ["AaosBorderBrush"] = "#27516B",
        ["AaosPrimaryBrush"] = "#2EC4B6",
        ["AaosPrimaryTextBrush"] = "#081020",
        ["AaosGoldBrush"] = "#F4D08B",
        ["AaosSuccessBrush"] = "#37C99A",
        ["AaosErrorBrush"] = "#E56464",
        ["AaosInfoBrush"] = "#3B82F6",
        ["AaosWarningBrush"] = "#E6BE73",
        ["AaosApprovalBrush"] = "#37C99A",
        ["AaosDisabledBrush"] = "#61747B",
        ["AaosReviewBrush"] = "#E6BE73",
        ["AaosIvoryBrush"] = "#F8F6EB",
        ["AaosMutedBrush"] = "#96AAB4",
        ["AaosOverlayBrush"] = "#9E081020",
        ["AaosPrimaryGradientEnd"] = "#63DED3",
        ["AaosBrandMarkEnd"] = "#2EC4B6",
        ["AaosGridBrush"] = "#0DFFFFFF",
        ["AaosAmbientPrimaryBrush"] = "#662EC4B6",
        ["AaosAmbientSecondaryBrush"] = "#55F4D08B",
        ["AaosAmbientTertiaryBrush"] = "#402EC4B6",
        ["AaosNavActiveStart"] = "#173B47",
        ["AaosNavActiveEnd"] = "#101D2E",
        ["AaosAmbientStart"] = "#2EC4B6",
        ["AaosAmbientMiddle"] = "#1B7775",
        ["AaosAmbientEnd"] = "#101D2E",
    };
}

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
        var colors = palette == Aurora ? AuroraColors : MonochromeColors;
        var resources = Application.Current?.Resources;
        if (resources is null)
            return;

        foreach (var (key, value) in colors)
            resources[key] = new SolidColorBrush(Color.Parse(value));

        resources["AaosGraphGlowColor"] = Color.Parse(palette == Aurora ? "#6622D6D2" : "#66E1E4E6");
        resources["AaosBrandMarkGlowEffect"] = new DropShadowEffect
        {
            Color = Color.Parse(palette == Aurora ? "#661FC8C5" : "#66E1E4E6"),
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
        var start = palette == Aurora ? "#37CAC7" : "#E2E5E7";
        var end = palette == Aurora ? "#90C291" : "#ADB4B8";
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
        ["AaosBackgroundBrush"] = "#061118",
        ["AaosSidebarBrush"] = "#091821",
        ["AaosSurfaceBrush"] = "#0C1C26",
        ["AaosSurface2Brush"] = "#102630",
        ["AaosBorderBrush"] = "#1D5055",
        ["AaosPrimaryBrush"] = "#1FC8C5",
        ["AaosPrimaryTextBrush"] = "#061118",
        ["AaosGoldBrush"] = "#E6BE73",
        ["AaosSuccessBrush"] = "#37C99A",
        ["AaosErrorBrush"] = "#E56464",
        ["AaosInfoBrush"] = "#3B82F6",
        ["AaosWarningBrush"] = "#E6BE73",
        ["AaosApprovalBrush"] = "#37C99A",
        ["AaosDisabledBrush"] = "#61747B",
        ["AaosReviewBrush"] = "#E6BE73",
        ["AaosIvoryBrush"] = "#F3EFE6",
        ["AaosMutedBrush"] = "#96AAB4",
        ["AaosOverlayBrush"] = "#9E061118",
        ["AaosPrimaryGradientEnd"] = "#63DED3",
        ["AaosBrandMarkEnd"] = "#8DC398",
        ["AaosGridBrush"] = "#0DFFFFFF",
        ["AaosAmbientPrimaryBrush"] = "#661FC8C5",
        ["AaosAmbientSecondaryBrush"] = "#55E6BE73",
        ["AaosAmbientTertiaryBrush"] = "#401FC8C5",
        ["AaosNavActiveStart"] = "#14343D",
        ["AaosNavActiveEnd"] = "#102630",
        ["AaosAmbientStart"] = "#1FC8C5",
        ["AaosAmbientMiddle"] = "#136F79",
        ["AaosAmbientEnd"] = "#0C1C26",
    };
}

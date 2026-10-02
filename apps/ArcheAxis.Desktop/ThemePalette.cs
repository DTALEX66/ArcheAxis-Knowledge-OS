using System;
using Avalonia;
using Avalonia.Media;
using Avalonia.Styling;
using System.Collections.Generic;

namespace ArcheAxis.Desktop;

/// <summary>Applies the two user-selectable AAOS palettes.</summary>
internal static class ThemePalette
{
    internal const string Black = "黑色主题";
    internal const string White = "白色主题";
    internal const string DeepSpace = "深空主题";
    internal const string Monochrome = Black;
    internal const string Ivory = White;
    internal const string Aurora = DeepSpace;
    internal static event EventHandler? PaletteChanged;
    public static void Apply(string palette)
    {
        var colors = palette switch
        {
            Ivory => IvoryColors,
            Monochrome => MonochromeColors,
            _ => AuroraColors,
        };
        var resources = Application.Current?.Resources;
        if (resources is null)
            return;

        foreach (var (key, value) in colors)
            resources[key] = new SolidColorBrush(Color.Parse(value));

        resources["AaosAcrylicMaterial"] = new ExperimentalAcrylicMaterial
        {
            BackgroundSource = AcrylicBackgroundSource.Digger,
            TintColor = Color.Parse(palette switch
            {
                White => "#F7F3E8",
                Black => "#171A1F",
                _ => "#101D2E",
            }),
            TintOpacity = palette == White ? 0.58 : 0.72,
            MaterialOpacity = palette == White ? 0.72 : 0.78,
            FallbackColor = Color.Parse(palette switch
            {
                White => "#99E6E0D2",
                Black => "#B8171A1F",
                _ => "#B8101D2E",
            }),
        };

        resources["AaosGraphGlowColor"] = Color.Parse(palette switch
        {
            Aurora => "#662EC4B6",
            Ivory => "#55147F78",
            _ => "#66E1E4E6",
        });
        resources["AaosBrandMarkGlowEffect"] = new DropShadowEffect
        {
            Color = Color.Parse(palette switch
            {
                Aurora => "#66F4D08B",
                Ivory => "#449A6F21",
                _ => "#66E1E4E6",
            }),
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
        var branded = palette is Aurora or Ivory;
        var start = branded ? colors["AaosGoldBrush"] : "#E2E5E7";
        var end = branded ? colors["AaosPrimaryBrush"] : "#ADB4B8";
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

    private static readonly IReadOnlyDictionary<string, string> IvoryColors = new Dictionary<string, string>
    {
        ["AaosBackgroundBrush"] = "#F8F6EB",
        ["AaosSidebarBrush"] = "#F0ECE1",
        ["AaosSurfaceBrush"] = "#FFFFFF",
        ["AaosSurface2Brush"] = "#ECE8DD",
        ["AaosBorderBrush"] = "#C8C2B4",
        ["AaosPrimaryBrush"] = "#147F78",
        ["AaosPrimaryTextBrush"] = "#FFFFFF",
        ["AaosGoldBrush"] = "#9A6F21",
        ["AaosSuccessBrush"] = "#187A59",
        ["AaosErrorBrush"] = "#B33A3A",
        ["AaosInfoBrush"] = "#245FA8",
        ["AaosWarningBrush"] = "#8A611C",
        ["AaosApprovalBrush"] = "#187A59",
        ["AaosDisabledBrush"] = "#7A807F",
        ["AaosReviewBrush"] = "#8A611C",
        ["AaosIvoryBrush"] = "#172033",
        ["AaosMutedBrush"] = "#586575",
        ["AaosOverlayBrush"] = "#66172033",
        ["AaosGlassBrush"] = "#99FFFFFF",
        ["AaosGlassRimBrush"] = "#997C927A",
        ["AaosHeroTextBrush"] = "#F8F6EB",
        ["AaosHeroMutedBrush"] = "#B7C8D1",
        ["AaosPrimaryGradientEnd"] = "#2EA49B",
        ["AaosBrandMarkEnd"] = "#147F78",
        ["AaosGridBrush"] = "#15172033",
        ["AaosAmbientPrimaryBrush"] = "#33147F78",
        ["AaosAmbientSecondaryBrush"] = "#339A6F21",
        ["AaosAmbientTertiaryBrush"] = "#24147F78",
        ["AaosNavActiveStart"] = "#D8EFEA",
        ["AaosNavActiveEnd"] = "#E8F3EF",
        ["AaosAmbientStart"] = "#D8EFEA",
        ["AaosAmbientMiddle"] = "#EDE4CB",
        ["AaosAmbientEnd"] = "#FFFFFF",
    };

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
        ["AaosGlassBrush"] = "#88171A1F",
        ["AaosGlassRimBrush"] = "#99C7CFD4",
        ["AaosHeroTextBrush"] = "#F1F2F3",
        ["AaosHeroMutedBrush"] = "#C4CBD0",
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
        ["AaosGlassBrush"] = "#7A101D2E",
        ["AaosGlassRimBrush"] = "#99B7E3E8",
        ["AaosHeroTextBrush"] = "#F8F6EB",
        ["AaosHeroMutedBrush"] = "#B7C8D1",
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

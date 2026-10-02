// Proposed UI metadata only. Do not replace existing handlers or Core contracts.
namespace ArcheAxis.Desktop.UiAdjustment;
public sealed record LegacyRoutePlacement(string Route, string Space, bool IsObjectDetail);
public static class LegacyRoutePlacements
{
    public static readonly LegacyRoutePlacement[] All =
    {
        new("home", "workbench", false),
        new("capture", "knowledge", false),
        new("library", "knowledge", false),
        new("search", "knowledge", false),
        new("source-reader", "knowledge", true),
        new("knowledge", "knowledge", false),
        new("original-editor", "knowledge", true),
        new("memory-map", "learning", false),
        new("learning", "learning", false),
        new("review", "learning", false),
        new("evidence", "evidence", false),
        new("research", "knowledge", false),
        new("machine-growth", "machine", false),
        new("workspace", "knowledge", false),
        new("jobs", "workbench", false),
        new("plugins", "system", false),
        new("models", "system", false),
        new("recovery", "system", false),
        new("settings", "system", false),
    };
}

using System.Text.Json;
using ArcheAxis.Desktop.Contracts.Generated;

if (args.Length != 1) throw new ArgumentException("Pass the shared vocabulary-cases.json path.");
using var cases = JsonDocument.Parse(File.ReadAllText(args[0]));
var count = 0;
foreach (var item in cases.RootElement.EnumerateArray())
{
    var category = item.GetProperty("category");
    var value = item.GetProperty("value");
    var accepted = false;
    if (category.ValueKind == JsonValueKind.String && value.ValueKind == JsonValueKind.String)
    {
        try { Vocabulary.Parse(category.GetString()!, value.GetString()!); accepted = true; }
        catch (ArgumentException) { }
    }
    if (accepted != item.GetProperty("valid").GetBoolean()) throw new Exception($"Wrong vocabulary acceptance: {item}");
    count++;
}
if (count == 0) throw new Exception("Empty fixtures cannot qualify a parser.");
Console.WriteLine($"PASS: {count} shared wire cases parsed by C# production vocabulary binding");

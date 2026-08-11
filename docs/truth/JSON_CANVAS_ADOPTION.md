# JSON Canvas Format Adoption (ADS-003)

## Source
- Spec: https://github.com/obsidianmd/jsoncanvas (MIT)
- Version: 1.0 (2024-01-18)

## Adoption Decision
Adopt the JSON Canvas **format** as the project's canonical canvas file representation.
This is format adoption, not library dependency — no code package is added.

## Format Summary
```jsonc
{
  "nodes": [
    {
      "id": "unique-string-id",
      "type": "text",     // or: file, link, group
      "x": 0,             // integer, canvas coordinate
      "y": 0,             // integer, canvas coordinate
      "width": 250,       // integer, minimum 1
      "height": 60,       // integer, minimum 1
      "color": "1",       // optional, preset: "1"-"6" or hex "#RRGGBB"
      "file": "path.md",  // only for type=file
      "url": "https://...",  // only for type=link
      "label": "string",  // only for type=group, optional
      "background": "string",  // only for type=group, optional
      "backgroundStyle": "cover"  // only for type=group, optional
    }
  ],
  "edges": [
    {
      "id": "unique-string-id",
      "fromNode": "node-id",
      "fromSide": "right",  // or: top, bottom, left
      "fromEnd": "none",    // or: arrow
      "toNode": "node-id",
      "toSide": "left",
      "toEnd": "arrow",
      "color": "1",         // optional
      "label": "string"     // optional
    }
  ]
}
```

## Project Integration Rules

1. **Read**: Parse JSON Canvas files. Unknown fields MUST be preserved on roundtrip.
2. **Write**: Emit valid JSON Canvas. Never invent non-standard fields.
3. **Coordinates**: Integers only. Non-integer values must be rounded and flagged.
4. **IDs**: Must be unique within the document. Generated IDs should use opaque strings (UUID or hash-based).
5. **Color Presets**: Accept "1"-"6" and "#RRGGBB". Reject invalid color values with a warning.
6. **Schema Validation**: Validate structure before ingestion; reject invalid documents with a clear error.

## Validator

See `shared/json_canvas.py` for the schema validator.

## Horizon

Target: H3 (Canvas/Workspace UI). Spec adopted now; visual rendering via XYFlow in H3.

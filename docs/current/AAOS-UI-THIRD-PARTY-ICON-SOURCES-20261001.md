# AAOS Reader 文件类型图标来源

状态：`IMPLEMENTED_LOCAL / SOURCE-VERIFIED`。这些图标仅给 Core `SourceMemberRow.OriginalName` 的已知文件扩展名选择矢量形状；扩展名不是 MIME 检测或可读性保证。未知扩展名、无原件名称仍使用 AAOS `Source` 图标。没有导入外部缩略图或业务数据。

| AAOS 图标 / Core 文件名扩展名 | 官方源文件（固定 ref `0.468.0`） | 官方 Git blob SHA | 原始 SVG SHA-256 | 目标 |
| --- | --- | --- | --- | --- |
| `FilePdf` / `.pdf` | [Lucide file-text.svg](https://github.com/lucide-icons/lucide/blob/0.468.0/icons/file-text.svg) | `5227939068ebaf76768cf348c04dd6c3db281a7d` | `486FAB70D8AD3CDC69B5FF9B6C356A58D41FCC4C885359CBF9D6E088A7C47F70` | `apps/ArcheAxis.Desktop/AaosIcon.axaml.cs` |
| `FileWord` / `.doc`, `.docx` | [Lucide file-type.svg](https://github.com/lucide-icons/lucide/blob/0.468.0/icons/file-type.svg) | `9ce95ae8a6a08e0f0e86f24bcd3ec457c90b461c` | `F9F3E9DDF1E5E8CE57B248BB47680290F300CD218A1E3CB001FDC870704284AD` | 同上 |
| `FileImage` / `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.tif`, `.tiff` | [Lucide file-image.svg](https://github.com/lucide-icons/lucide/blob/0.468.0/icons/file-image.svg) | `eb2f905b06b6ec61eb67de7c3098baed7130ba45` | `258B199A41DECA975018E808568F017ADC11BA1C5B1FFB7A956DAA0E22F30A35` | 同上 |

原仓库：[Lucide](https://github.com/lucide-icons/lucide/tree/0.468.0)，许可证：[ISC，固定版本原文](https://github.com/lucide-icons/lucide/blob/0.468.0/LICENSE)。`AaosIcon` 将原 SVG 的线段和圆转换为 Avalonia `Geometry`，沿用已有 `Foreground`、1.7 DIP 线宽与圆角端点，未引入运行时包。分发时保留 Lucide 官方许可文本和 copyright notice；应与最终资产清单一起校验。

该固定 ref 的 `LICENSE` 原始 SHA-256 为 `1E7290B35280A048667BBF0EBABAC1C7FD52A75300E8B2946AC165715997F2BC`。为便于后续候选包携带许可，下面保存原文；最终打包时仍需核查 NOTICE 收录：

```text
ISC License

Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT). All other copyright (c) for Lucide are held by Lucide Contributors 2022.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

9 月 28 日资源快照推荐的 Microsoft Fluent System Icons `1.1.343` 经上游 GitHub API 核对，该 ref 的 `assets` 顶层有 `Document Image`，未找到 `Document PDF` 或 `Document Word`。因此本切片按 9 月 30 日 UI14 选择 Lucide 的三个固定 SVG，未猜造 Fluent SVG 文件路径或安装整个库。

变更范围：`SourceReaderView.axaml.cs` 仅根据 `OriginalName` 扩展名给成员行选图标；任务行和无原件名称的成员保持原图标。颜色由 AAOS 主题令牌决定，图标不表示 Core 类型检测、转换成功或证据验证。

验证：Avalonia Debug build 0 warning / 0 error；Reader 两份针对测试 7 passed（已更新过时的 `DisplayIcon => "Source"` 静态断言）；隔离原生 Avalonia 预览直接用 `SourceMemberRow` 的合成文件名构造四行，截图位于 `.project-local/runs/22cad761f8/ui-icon-preview-20261001/icons.png`，SHA-256 `313D92BF44A2DAD5FBDB7E4F2FB65735EEC3BFD5CC24477158E5EDF61CB71B54`。预览只证明图标几何可渲染及扩展名映射，不证明任何真实文件已导入、Core 检测或完整 Reader 运行。

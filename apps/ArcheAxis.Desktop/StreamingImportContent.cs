using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace ArcheAxis.Desktop;

// Keep the existing JSON contract without buffering the whole source and base64 text.
// The caller owns the source stream; HttpClient owns the destination stream.
internal sealed class StreamingImportContent : HttpContent
{
    private readonly Stream _source;
    private readonly byte[] _prefix;
    private static readonly byte[] Suffix = Encoding.UTF8.GetBytes("\"}");

    public StreamingImportContent(string name, Stream source)
    {
        _source = source;
        _prefix = Encoding.UTF8.GetBytes("{\"name\":" + JsonSerializer.Serialize(name) + ",\"content_base64\":\"");
        Headers.ContentType = new MediaTypeHeaderValue("application/json") { CharSet = "utf-8" };
    }

    protected override bool TryComputeLength(out long length)
    {
        length = 0;
        return false;
    }

    protected override Task SerializeToStreamAsync(Stream stream, TransportContext? context)
        => SerializeToStreamAsync(stream, context, CancellationToken.None);

    protected override async Task SerializeToStreamAsync(Stream stream, TransportContext? context, CancellationToken cancellationToken)
    {
        await stream.WriteAsync(_prefix, cancellationToken).ConfigureAwait(false);
        using var transform = new ToBase64Transform();
        using (var encoded = new CryptoStream(stream, transform, CryptoStreamMode.Write, leaveOpen: true))
        {
            await _source.CopyToAsync(encoded, 64 * 1024, cancellationToken).ConfigureAwait(false);
            await encoded.FlushFinalBlockAsync(cancellationToken).ConfigureAwait(false);
        }
        await stream.WriteAsync(Suffix, cancellationToken).ConfigureAwait(false);
    }
}

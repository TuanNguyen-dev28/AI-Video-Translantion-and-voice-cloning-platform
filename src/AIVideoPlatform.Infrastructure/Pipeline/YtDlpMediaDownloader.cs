using System;
using System.Threading.Tasks;
using AIVideoPlatform.Application.Interfaces.Pipeline;

namespace AIVideoPlatform.Infrastructure.Pipeline;

public class YtDlpMediaDownloader : IMediaDownloader
{
    public Task<string> DownloadAsync(string url, string outputDir)
    {
        // TODO: Call yt-dlp process
        return Task.FromResult(System.IO.Path.Combine(outputDir, "downloaded.mp4"));
    }
}

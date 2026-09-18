using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public interface IMediaDownloader
{
    Task<string> DownloadAsync(string url, string outputDir);
}

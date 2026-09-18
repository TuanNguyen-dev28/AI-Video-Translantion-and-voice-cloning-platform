using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public interface ITtsProvider
{
    Task<string> GenerateSpeechAsync(string text, string voiceId, string outputDir);
}

using System.Threading.Tasks;
using AIVideoPlatform.Application.Interfaces.Pipeline;

namespace AIVideoPlatform.Infrastructure.Pipeline;

public class DemucsAudioSeparator : IAudioSeparator
{
    public Task<SeparationResult> SeparateAsync(string audioPath)
    {
        // TODO: Call Demucs
        return Task.FromResult(new SeparationResult());
    }
}

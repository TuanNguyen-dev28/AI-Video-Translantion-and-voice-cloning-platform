using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public class SeparationResult { public string VocalsPath {get;set;} public string BackgroundPath {get;set;} }

public interface IAudioSeparator
{
    Task<SeparationResult> SeparateAsync(string audioPath);
}

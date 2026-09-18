using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public class Transcript { public string Text {get;set;} }

public interface IAsrProvider
{
    Task<Transcript> TranscribeAsync(string audioPath);
}

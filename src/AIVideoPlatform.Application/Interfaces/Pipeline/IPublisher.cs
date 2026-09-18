using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public interface IPublisher
{
    Task<bool> PublishAsync(string videoPath, string metadataJson);
}

using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces;

public interface IEventPublisher
{
    Task PublishJobEventAsync(string queueName, object message);
}

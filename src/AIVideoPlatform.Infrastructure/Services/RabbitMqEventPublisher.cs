using System.Threading.Tasks;
using AIVideoPlatform.Application.Interfaces;

namespace AIVideoPlatform.Infrastructure.Services;

public class RabbitMqEventPublisher : IEventPublisher
{
    // Dummy implementation for RabbitMQ
    public Task PublishJobEventAsync(string queueName, object message)
    {
        // TODO: Integrate RabbitMQ SDK (RabbitMQ.Client)
        return Task.CompletedTask;
    }
}

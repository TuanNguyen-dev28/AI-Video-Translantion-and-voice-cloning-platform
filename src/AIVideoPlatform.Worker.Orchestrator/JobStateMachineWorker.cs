using System;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace AIVideoPlatform.Worker.Orchestrator;

public class JobStateMachineWorker : BackgroundService
{
    private readonly ILogger<JobStateMachineWorker> _logger;

    public JobStateMachineWorker(ILogger<JobStateMachineWorker> logger)
    {
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Orchestrator Worker starting. Listening to RabbitMQ...");
        while (!stoppingToken.IsCancellationRequested)
        {
            // TODO: Read from orchestrator_queue
            // Transition State Machine:
            // QUEUED -> RESERVING_CREDITS
            // RESERVING_CREDITS -> DOWNLOADING (dispatch to media_queue)
            await Task.Delay(5000, stoppingToken);
        }
    }
}

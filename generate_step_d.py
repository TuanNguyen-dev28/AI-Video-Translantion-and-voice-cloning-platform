import os

app_interfaces = 'src/AIVideoPlatform.Application/Interfaces'
app_services = 'src/AIVideoPlatform.Application/Services'
infra_services = 'src/AIVideoPlatform.Infrastructure/Services'
worker_orch = 'src/AIVideoPlatform.Worker.Orchestrator'

os.makedirs(app_interfaces, exist_ok=True)
os.makedirs(app_services, exist_ok=True)
os.makedirs(infra_services, exist_ok=True)

icredit_code = '''using System;
using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces;

public interface ICreditService
{
    Task<bool> ReserveCreditsAsync(Guid userId, decimal estimatedCost);
    Task DeductCreditsAsync(Guid jobId);
    Task RefundCreditsAsync(Guid jobId);
}
'''
with open(os.path.join(app_interfaces, 'ICreditService.cs'), 'w', encoding='utf-8') as f: f.write(icredit_code)

ijob_code = '''using System;
using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces;

public interface IJobService
{
    Task<Guid> CreateJobAsync(Guid userId, string url, string targetLanguage);
    Task CancelJobAsync(Guid jobId);
    Task UpdateJobProgressAsync(Guid jobId, string stepName, string status);
    Task RetryJobAsync(Guid jobId);
}
'''
with open(os.path.join(app_interfaces, 'IJobService.cs'), 'w', encoding='utf-8') as f: f.write(ijob_code)

ievent_code = '''using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces;

public interface IEventPublisher
{
    Task PublishJobEventAsync(string queueName, object message);
}
'''
with open(os.path.join(app_interfaces, 'IEventPublisher.cs'), 'w', encoding='utf-8') as f: f.write(ievent_code)

credit_code = '''using System;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using AIVideoPlatform.Application.Interfaces;
using AIVideoPlatform.Domain.Interfaces;
using AIVideoPlatform.Domain.Entities;
using AIVideoPlatform.Domain.Enums;
using System.Linq;

namespace AIVideoPlatform.Application.Services;

public class CreditService : ICreditService
{
    private readonly IRepository<Wallet> _walletRepo;
    private readonly IRepository<CreditTransaction> _transactionRepo;
    private readonly IUnitOfWork _unitOfWork;

    public CreditService(IRepository<Wallet> walletRepo, IRepository<CreditTransaction> transactionRepo, IUnitOfWork unitOfWork)
    {
        _walletRepo = walletRepo;
        _transactionRepo = transactionRepo;
        _unitOfWork = unitOfWork;
    }

    public async Task<bool> ReserveCreditsAsync(Guid userId, decimal estimatedCost)
    {
        var wallets = await _walletRepo.GetAllAsync();
        var wallet = wallets.FirstOrDefault(w => w.UserId == userId);
        if (wallet == null || wallet.Balance < estimatedCost) return false;

        wallet.Balance -= estimatedCost;
        wallet.ReservedBalance += estimatedCost;
        
        await _transactionRepo.AddAsync(new CreditTransaction
        {
            WalletId = wallet.Id,
            Type = TransactionType.RESERVE,
            Amount = estimatedCost,
            ReferenceId = "Estimation"
        });

        _walletRepo.Update(wallet);
        await _unitOfWork.SaveChangesAsync();
        return true;
    }

    public async Task DeductCreditsAsync(Guid jobId)
    {
        // Dummy logic for deducting actual usage cost.
        await Task.CompletedTask;
    }

    public async Task RefundCreditsAsync(Guid jobId)
    {
        await Task.CompletedTask;
    }
}
'''
with open(os.path.join(app_services, 'CreditService.cs'), 'w', encoding='utf-8') as f: f.write(credit_code)

job_code = '''using System;
using System.Threading.Tasks;
using AIVideoPlatform.Application.Interfaces;
using AIVideoPlatform.Domain.Interfaces;
using AIVideoPlatform.Domain.Entities;
using AIVideoPlatform.Domain.Enums;

namespace AIVideoPlatform.Application.Services;

public class JobService : IJobService
{
    private readonly IRepository<Job> _jobRepo;
    private readonly IUnitOfWork _unitOfWork;
    private readonly IEventPublisher _eventPublisher;

    public JobService(IRepository<Job> jobRepo, IUnitOfWork unitOfWork, IEventPublisher eventPublisher)
    {
        _jobRepo = jobRepo;
        _unitOfWork = unitOfWork;
        _eventPublisher = eventPublisher;
    }

    public async Task<Guid> CreateJobAsync(Guid userId, string url, string targetLanguage)
    {
        var job = new Job
        {
            UserId = userId,
            OriginalUrl = url,
            TargetLanguage = targetLanguage,
            Status = JobStatus.QUEUED
        };

        await _jobRepo.AddAsync(job);
        await _unitOfWork.SaveChangesAsync();

        // Queue event
        await _eventPublisher.PublishJobEventAsync("orchestrator_queue", new { JobId = job.Id, EventType = "JobCreated" });

        return job.Id;
    }

    public async Task CancelJobAsync(Guid jobId) { await Task.CompletedTask; }
    public async Task UpdateJobProgressAsync(Guid jobId, string stepName, string status) { await Task.CompletedTask; }
    public async Task RetryJobAsync(Guid jobId) { await Task.CompletedTask; }
}
'''
with open(os.path.join(app_services, 'JobService.cs'), 'w', encoding='utf-8') as f: f.write(job_code)

rabbit_code = '''using System.Threading.Tasks;
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
'''
with open(os.path.join(infra_services, 'RabbitMqEventPublisher.cs'), 'w', encoding='utf-8') as f: f.write(rabbit_code)

orch_code = '''using System;
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
'''
with open(os.path.join(worker_orch, 'JobStateMachineWorker.cs'), 'w', encoding='utf-8') as f: f.write(orch_code)

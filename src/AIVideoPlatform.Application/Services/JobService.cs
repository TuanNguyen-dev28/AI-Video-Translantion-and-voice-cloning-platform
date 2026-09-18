using System;
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

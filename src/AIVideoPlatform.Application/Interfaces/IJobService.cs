using System;
using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces;

public interface IJobService
{
    Task<Guid> CreateJobAsync(Guid userId, string url, string targetLanguage);
    Task CancelJobAsync(Guid jobId);
    Task UpdateJobProgressAsync(Guid jobId, string stepName, string status);
    Task RetryJobAsync(Guid jobId);
}

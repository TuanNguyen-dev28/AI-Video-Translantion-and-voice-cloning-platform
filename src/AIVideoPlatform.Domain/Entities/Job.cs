using System;
using System.Collections.Generic;
using AIVideoPlatform.Domain.Enums;

namespace AIVideoPlatform.Domain.Entities;

public class Job
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid UserId { get; set; }
    public string OriginalUrl { get; set; } = string.Empty;
    public string TargetLanguage { get; set; } = string.Empty;
    public JobStatus Status { get; set; } = JobStatus.QUEUED;
    public string ErrorMessage { get; set; } = string.Empty;
    public DateTime StartedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }
    
    public User User { get; set; }
    public ICollection<JobStep> Steps { get; set; } = new List<JobStep>();
    public ICollection<JobArtifact> Artifacts { get; set; } = new List<JobArtifact>();
    public ICollection<ProviderUsage> ProviderUsages { get; set; } = new List<ProviderUsage>();
}

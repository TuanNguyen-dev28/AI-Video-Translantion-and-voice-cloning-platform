using System;
using AIVideoPlatform.Domain.Enums;

namespace AIVideoPlatform.Domain.Entities;

public class JobStep
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid JobId { get; set; }
    public string StepName { get; set; } = string.Empty;
    public StepStatus Status { get; set; } = StepStatus.PENDING;
    public int RetryCount { get; set; }
    public DateTime StartedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }
    
    public Job Job { get; set; }
}

using System;

namespace AIVideoPlatform.Domain.Entities;

public class Plan
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = string.Empty;
    public int QuotaMinutes { get; set; }
    public int MaxConcurrentJobs { get; set; }
}

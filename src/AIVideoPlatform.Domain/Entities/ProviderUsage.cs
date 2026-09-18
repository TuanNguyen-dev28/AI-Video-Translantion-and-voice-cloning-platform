using System;

namespace AIVideoPlatform.Domain.Entities;

public class ProviderUsage
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid JobId { get; set; }
    public string ProviderName { get; set; } = string.Empty;
    public string Operation { get; set; } = string.Empty;
    public decimal Cost { get; set; }
    public int DurationMs { get; set; }
    
    public Job Job { get; set; }
}

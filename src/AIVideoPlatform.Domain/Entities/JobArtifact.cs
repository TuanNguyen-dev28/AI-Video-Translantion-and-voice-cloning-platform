using System;

namespace AIVideoPlatform.Domain.Entities;

public class JobArtifact
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid JobId { get; set; }
    public string ArtifactType { get; set; } = string.Empty;
    public string S3Path { get; set; } = string.Empty;
    
    public Job Job { get; set; }
}

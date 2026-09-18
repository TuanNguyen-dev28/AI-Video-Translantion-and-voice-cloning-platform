using System;
using System.Collections.Generic;

namespace AIVideoPlatform.Domain.Entities;

public class User
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Email { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
    public string Role { get; set; } = "User";
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    public Wallet Wallet { get; set; }
    public ICollection<Job> Jobs { get; set; } = new List<Job>();
}

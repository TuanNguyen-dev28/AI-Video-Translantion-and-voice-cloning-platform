using System;
using AIVideoPlatform.Domain.Enums;

namespace AIVideoPlatform.Domain.Entities;

public class CreditTransaction
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid WalletId { get; set; }
    public TransactionType Type { get; set; }
    public decimal Amount { get; set; }
    public string ReferenceId { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    public Wallet Wallet { get; set; }
}

using System;
using System.Collections.Generic;

namespace AIVideoPlatform.Domain.Entities;

public class Wallet
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid UserId { get; set; }
    public decimal Balance { get; set; }
    public decimal ReservedBalance { get; set; }
    
    public User User { get; set; }
    public ICollection<CreditTransaction> Transactions { get; set; } = new List<CreditTransaction>();
}

using System;
using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces;

public interface ICreditService
{
    Task<bool> ReserveCreditsAsync(Guid userId, decimal estimatedCost);
    Task DeductCreditsAsync(Guid jobId);
    Task RefundCreditsAsync(Guid jobId);
}

using System;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using AIVideoPlatform.Application.Interfaces;
using AIVideoPlatform.Domain.Interfaces;
using AIVideoPlatform.Domain.Entities;
using AIVideoPlatform.Domain.Enums;
using System.Linq;

namespace AIVideoPlatform.Application.Services;

public class CreditService : ICreditService
{
    private readonly IRepository<Wallet> _walletRepo;
    private readonly IRepository<CreditTransaction> _transactionRepo;
    private readonly IUnitOfWork _unitOfWork;

    public CreditService(IRepository<Wallet> walletRepo, IRepository<CreditTransaction> transactionRepo, IUnitOfWork unitOfWork)
    {
        _walletRepo = walletRepo;
        _transactionRepo = transactionRepo;
        _unitOfWork = unitOfWork;
    }

    public async Task<bool> ReserveCreditsAsync(Guid userId, decimal estimatedCost)
    {
        var wallets = await _walletRepo.GetAllAsync();
        var wallet = wallets.FirstOrDefault(w => w.UserId == userId);
        if (wallet == null || wallet.Balance < estimatedCost) return false;

        wallet.Balance -= estimatedCost;
        wallet.ReservedBalance += estimatedCost;
        
        await _transactionRepo.AddAsync(new CreditTransaction
        {
            WalletId = wallet.Id,
            Type = TransactionType.RESERVE,
            Amount = estimatedCost,
            ReferenceId = "Estimation"
        });

        _walletRepo.Update(wallet);
        await _unitOfWork.SaveChangesAsync();
        return true;
    }

    public async Task DeductCreditsAsync(Guid jobId)
    {
        // Dummy logic for deducting actual usage cost.
        await Task.CompletedTask;
    }

    public async Task RefundCreditsAsync(Guid jobId)
    {
        await Task.CompletedTask;
    }
}

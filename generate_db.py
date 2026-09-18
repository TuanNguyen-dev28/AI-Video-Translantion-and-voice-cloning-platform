import os

domain_dir = 'src/AIVideoPlatform.Domain/Entities'
enum_dir = 'src/AIVideoPlatform.Domain/Enums'
interfaces_dir = 'src/AIVideoPlatform.Domain/Interfaces'
infra_dir = 'src/AIVideoPlatform.Infrastructure/Persistence'
repo_dir = 'src/AIVideoPlatform.Infrastructure/Persistence/Repositories'

os.makedirs(domain_dir, exist_ok=True)
os.makedirs(enum_dir, exist_ok=True)
os.makedirs(interfaces_dir, exist_ok=True)
os.makedirs(infra_dir, exist_ok=True)
os.makedirs(repo_dir, exist_ok=True)

enums_code = '''namespace AIVideoPlatform.Domain.Enums;

public enum JobStatus
{
    QUEUED, RESERVING_CREDITS, DOWNLOADING, ANALYZING, EXTRACTING_AUDIO, 
    SEPARATING_AUDIO, TRANSCRIBING, SEGMENT_ANALYSIS, TRANSLATING, 
    TRANSLATION_QA, GENERATING_TTS, FITTING_TTS, BUILDING_TIMELINE, 
    MIXING_AUDIO, GENERATING_SUBTITLE, RENDERING_VIDEO, VALIDATING_OUTPUT, 
    GENERATING_METADATA, UPLOADING_YOUTUBE, COMPLETED, FAILED, CANCELLED, REFUNDING
}

public enum StepStatus
{
    PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
}

public enum TransactionType
{
    TOPUP, RESERVE, DEDUCT, REFUND
}
'''
with open(os.path.join(enum_dir, 'Enums.cs'), 'w', encoding='utf-8') as f: f.write(enums_code)

user_code = '''using System;
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
'''
with open(os.path.join(domain_dir, 'User.cs'), 'w', encoding='utf-8') as f: f.write(user_code)

plan_code = '''using System;

namespace AIVideoPlatform.Domain.Entities;

public class Plan
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = string.Empty;
    public int QuotaMinutes { get; set; }
    public int MaxConcurrentJobs { get; set; }
}
'''
with open(os.path.join(domain_dir, 'Plan.cs'), 'w', encoding='utf-8') as f: f.write(plan_code)

wallet_code = '''using System;
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
'''
with open(os.path.join(domain_dir, 'Wallet.cs'), 'w', encoding='utf-8') as f: f.write(wallet_code)

transaction_code = '''using System;
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
'''
with open(os.path.join(domain_dir, 'CreditTransaction.cs'), 'w', encoding='utf-8') as f: f.write(transaction_code)

job_code = '''using System;
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
'''
with open(os.path.join(domain_dir, 'Job.cs'), 'w', encoding='utf-8') as f: f.write(job_code)

jobstep_code = '''using System;
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
'''
with open(os.path.join(domain_dir, 'JobStep.cs'), 'w', encoding='utf-8') as f: f.write(jobstep_code)

jobartifact_code = '''using System;

namespace AIVideoPlatform.Domain.Entities;

public class JobArtifact
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid JobId { get; set; }
    public string ArtifactType { get; set; } = string.Empty;
    public string S3Path { get; set; } = string.Empty;
    
    public Job Job { get; set; }
}
'''
with open(os.path.join(domain_dir, 'JobArtifact.cs'), 'w', encoding='utf-8') as f: f.write(jobartifact_code)

providerusage_code = '''using System;

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
'''
with open(os.path.join(domain_dir, 'ProviderUsage.cs'), 'w', encoding='utf-8') as f: f.write(providerusage_code)

irepo_code = '''using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace AIVideoPlatform.Domain.Interfaces;

public interface IRepository<T> where T : class
{
    Task<T> GetByIdAsync(Guid id);
    Task<IEnumerable<T>> GetAllAsync();
    Task AddAsync(T entity);
    void Update(T entity);
    void Delete(T entity);
}
'''
with open(os.path.join(interfaces_dir, 'IRepository.cs'), 'w', encoding='utf-8') as f: f.write(irepo_code)

iuow_code = '''using System.Threading.Tasks;

namespace AIVideoPlatform.Domain.Interfaces;

public interface IUnitOfWork
{
    Task<int> SaveChangesAsync();
}
'''
with open(os.path.join(interfaces_dir, 'IUnitOfWork.cs'), 'w', encoding='utf-8') as f: f.write(iuow_code)

dbcontext_code = '''using Microsoft.EntityFrameworkCore;
using AIVideoPlatform.Domain.Entities;

namespace AIVideoPlatform.Infrastructure.Persistence;

public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options) { }
    
    public DbSet<User> Users { get; set; }
    public DbSet<Plan> Plans { get; set; }
    public DbSet<Wallet> Wallets { get; set; }
    public DbSet<CreditTransaction> CreditTransactions { get; set; }
    public DbSet<Job> Jobs { get; set; }
    public DbSet<JobStep> JobSteps { get; set; }
    public DbSet<JobArtifact> JobArtifacts { get; set; }
    public DbSet<ProviderUsage> ProviderUsages { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);
        
        // Define relations
        modelBuilder.Entity<User>()
            .HasOne(u => u.Wallet)
            .WithOne(w => w.User)
            .HasForeignKey<Wallet>(w => w.UserId);
            
        modelBuilder.Entity<Wallet>()
            .HasMany(w => w.Transactions)
            .WithOne(t => t.Wallet)
            .HasForeignKey(t => t.WalletId);
            
        modelBuilder.Entity<User>()
            .HasMany(u => u.Jobs)
            .WithOne(j => j.User)
            .HasForeignKey(j => j.UserId);
            
        modelBuilder.Entity<Job>()
            .HasMany(j => j.Steps)
            .WithOne(s => s.Job)
            .HasForeignKey(s => s.JobId);
            
        modelBuilder.Entity<Job>()
            .HasMany(j => j.Artifacts)
            .WithOne(a => a.Job)
            .HasForeignKey(a => a.JobId);
            
        modelBuilder.Entity<Job>()
            .HasMany(j => j.ProviderUsages)
            .WithOne(p => p.Job)
            .HasForeignKey(p => p.JobId);
    }
}
'''
with open(os.path.join(infra_dir, 'ApplicationDbContext.cs'), 'w', encoding='utf-8') as f: f.write(dbcontext_code)

repo_code = '''using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using AIVideoPlatform.Domain.Interfaces;

namespace AIVideoPlatform.Infrastructure.Persistence.Repositories;

public class Repository<T> : IRepository<T> where T : class
{
    protected readonly ApplicationDbContext _context;
    protected readonly DbSet<T> _dbSet;
    
    public Repository(ApplicationDbContext context)
    {
        _context = context;
        _dbSet = context.Set<T>();
    }
    
    public async Task<T> GetByIdAsync(Guid id) => await _dbSet.FindAsync(id);
    public async Task<IEnumerable<T>> GetAllAsync() => await _dbSet.ToListAsync();
    public async Task AddAsync(T entity) => await _dbSet.AddAsync(entity);
    public void Update(T entity) => _dbSet.Update(entity);
    public void Delete(T entity) => _dbSet.Remove(entity);
}
'''
with open(os.path.join(repo_dir, 'Repository.cs'), 'w', encoding='utf-8') as f: f.write(repo_code)

uow_code = '''using System.Threading.Tasks;
using AIVideoPlatform.Domain.Interfaces;

namespace AIVideoPlatform.Infrastructure.Persistence.Repositories;

public class UnitOfWork : IUnitOfWork
{
    private readonly ApplicationDbContext _context;
    
    public UnitOfWork(ApplicationDbContext context)
    {
        _context = context;
    }
    
    public async Task<int> SaveChangesAsync()
    {
        return await _context.SaveChangesAsync();
    }
}
'''
with open(os.path.join(repo_dir, 'UnitOfWork.cs'), 'w', encoding='utf-8') as f: f.write(uow_code)

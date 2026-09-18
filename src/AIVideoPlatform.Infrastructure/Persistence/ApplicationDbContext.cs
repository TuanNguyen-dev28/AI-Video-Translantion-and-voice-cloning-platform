using Microsoft.EntityFrameworkCore;
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

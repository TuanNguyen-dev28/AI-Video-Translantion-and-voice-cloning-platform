using System.Threading.Tasks;

namespace AIVideoPlatform.Domain.Interfaces;

public interface IUnitOfWork
{
    Task<int> SaveChangesAsync();
}

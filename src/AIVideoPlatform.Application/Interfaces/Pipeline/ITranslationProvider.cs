using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public class TranslationResult { public string TranslatedText {get;set;} }

public interface ITranslationProvider
{
    Task<TranslationResult> TranslateAsync(Transcript transcript, string targetLang);
}

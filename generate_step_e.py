import os

app_pipe = 'src/AIVideoPlatform.Application/Interfaces/Pipeline'
infra_pipe = 'src/AIVideoPlatform.Infrastructure/Pipeline'

os.makedirs(app_pipe, exist_ok=True)
os.makedirs(infra_pipe, exist_ok=True)

downloader_int = '''using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public interface IMediaDownloader
{
    Task<string> DownloadAsync(string url, string outputDir);
}
'''
with open(os.path.join(app_pipe, 'IMediaDownloader.cs'), 'w', encoding='utf-8') as f: f.write(downloader_int)

separator_int = '''using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public class SeparationResult { public string VocalsPath {get;set;} public string BackgroundPath {get;set;} }

public interface IAudioSeparator
{
    Task<SeparationResult> SeparateAsync(string audioPath);
}
'''
with open(os.path.join(app_pipe, 'IAudioSeparator.cs'), 'w', encoding='utf-8') as f: f.write(separator_int)

asr_int = '''using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public class Transcript { public string Text {get;set;} }

public interface IAsrProvider
{
    Task<Transcript> TranscribeAsync(string audioPath);
}
'''
with open(os.path.join(app_pipe, 'IAsrProvider.cs'), 'w', encoding='utf-8') as f: f.write(asr_int)

translate_int = '''using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public class TranslationResult { public string TranslatedText {get;set;} }

public interface ITranslationProvider
{
    Task<TranslationResult> TranslateAsync(Transcript transcript, string targetLang);
}
'''
with open(os.path.join(app_pipe, 'ITranslationProvider.cs'), 'w', encoding='utf-8') as f: f.write(translate_int)

tts_int = '''using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public interface ITtsProvider
{
    Task<string> GenerateSpeechAsync(string text, string voiceId, string outputDir);
}
'''
with open(os.path.join(app_pipe, 'ITtsProvider.cs'), 'w', encoding='utf-8') as f: f.write(tts_int)

publisher_int = '''using System.Threading.Tasks;

namespace AIVideoPlatform.Application.Interfaces.Pipeline;

public interface IPublisher
{
    Task<bool> PublishAsync(string videoPath, string metadataJson);
}
'''
with open(os.path.join(app_pipe, 'IPublisher.cs'), 'w', encoding='utf-8') as f: f.write(publisher_int)

# Infrastructure Dummy Implementations
ytdlp_code = '''using System;
using System.Threading.Tasks;
using AIVideoPlatform.Application.Interfaces.Pipeline;

namespace AIVideoPlatform.Infrastructure.Pipeline;

public class YtDlpMediaDownloader : IMediaDownloader
{
    public Task<string> DownloadAsync(string url, string outputDir)
    {
        // TODO: Call yt-dlp process
        return Task.FromResult(System.IO.Path.Combine(outputDir, "downloaded.mp4"));
    }
}
'''
with open(os.path.join(infra_pipe, 'YtDlpMediaDownloader.cs'), 'w', encoding='utf-8') as f: f.write(ytdlp_code)

demucs_code = '''using System.Threading.Tasks;
using AIVideoPlatform.Application.Interfaces.Pipeline;

namespace AIVideoPlatform.Infrastructure.Pipeline;

public class DemucsAudioSeparator : IAudioSeparator
{
    public Task<SeparationResult> SeparateAsync(string audioPath)
    {
        // TODO: Call Demucs
        return Task.FromResult(new SeparationResult());
    }
}
'''
with open(os.path.join(infra_pipe, 'DemucsAudioSeparator.cs'), 'w', encoding='utf-8') as f: f.write(demucs_code)

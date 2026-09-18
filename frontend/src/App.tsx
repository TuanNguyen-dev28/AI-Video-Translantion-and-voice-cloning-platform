import { useState, useEffect, useCallback } from 'react';
import PipelineForm from './PipelineForm';
import LogViewer from './LogViewer';
import StepProgress from './StepProgress';

const API_BASE = import.meta.env.VITE_API_URL || '';

interface JobResult {
  success: boolean;
  youtube_url?: string;
  facebook_url?: string;
  output_dir?: string;
  dubbed_video?: string;
  metadata?: Record<string, string>;
  upload_pending?: boolean;
  error?: string;
}

function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  // Poll for final status
  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/status/${jobId}`);
        const data = await res.json();
        if (data.status === 'completed' || data.status === 'failed') {
          setResult(data.result);
          clearInterval(interval);
        }
      } catch (err) {
        console.error(err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [jobId]);

  const handleLogUpdate = useCallback((newLogs: string[]) => {
    setLogs(newLogs);
  }, []);

  const handleJobStarted = useCallback((id: string) => {
    setJobId(id);
    setResult(null);
    setLogs([]);
  }, []);

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Animated Gradient Header */}
      <header className="bg-gradient-to-r from-indigo-600 via-purple-600 to-cyan-500 animate-gradient py-10 px-4">
        <div className="max-w-6xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight drop-shadow-lg">
            🎬 AI Video Translation
          </h1>
          <p className="mt-3 text-lg md:text-xl text-white/80">
            Tự động dịch và lồng tiếng Việt cho video YouTube, TikTok, Douyin
          </p>
          <p className="mt-1 text-sm text-white/50">
            Local-first: audio và transcript xử lý trên máy của bạn — xuất bản cần duyệt riêng
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

          {/* Left Panel - Form (2/5) */}
          <div className="lg:col-span-2">
            <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700/50 shadow-xl sticky top-8">
              <h2 className="text-xl font-bold mb-5 text-indigo-400 flex items-center gap-2">
                📥 Cấu hình
              </h2>
              <PipelineForm onJobStarted={handleJobStarted} />
            </div>
          </div>

          {/* Right Panel - Progress & Results (3/5) */}
          <div className="lg:col-span-3 space-y-6">

            {/* Step Progress */}
            <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700/50 shadow-xl">
              <h2 className="text-xl font-bold mb-4 text-indigo-400 flex items-center gap-2">
                ⚡ Pipeline Progress
              </h2>
              <StepProgress logs={logs} />
            </div>

            {/* Log Viewer */}
            <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700/50 shadow-xl">
              <h2 className="text-lg font-bold mb-3 text-slate-300 flex items-center gap-2">
                📋 Logs
              </h2>
              <LogViewer jobId={jobId} onLogUpdate={handleLogUpdate} />
            </div>

            {/* Results */}
            <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700/50 shadow-xl fade-in">
              <h2 className="text-xl font-bold mb-4 text-indigo-400 flex items-center gap-2">
                ✅ Kết quả
              </h2>

              {result ? (
                <div className={`rounded-lg border p-5 ${result.success ? 'bg-green-500/5 border-green-500/30' : 'bg-red-500/5 border-red-500/30'}`}>
                  {result.success ? (
                    <div className="space-y-4">
                      <p className="text-green-400 font-semibold text-lg">✓ Pipeline hoàn thành!</p>

                      {/* Video Player */}
                      {jobId && (
                        <div className="rounded-lg overflow-hidden bg-black">
                          <video
                            controls
                            className="w-full max-h-96"
                            src={`${API_BASE}/api/video/${jobId}`}
                          >
                            Trình duyệt không hỗ trợ video.
                          </video>
                        </div>
                      )}

                      {result.upload_pending && (
                        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                          <p className="text-amber-300 text-sm">
                            ⏳ Video đã tạo xong và đang chờ duyệt. Bạn có thể xem video ở trên trước khi quyết định.
                          </p>
                          <button
                            onClick={async () => {
                              try {
                                const res = await fetch(`${API_BASE}/api/publish/${jobId}`, { method: 'POST' });
                                if (!res.ok) throw new Error('API Error');
                                alert('Đã gửi lệnh đăng tải! Vui lòng xem logs để theo dõi tiến trình.');
                              } catch (e) {
                                alert('Lỗi khi gửi yêu cầu đăng tải');
                              }
                            }}
                            className="bg-amber-600 hover:bg-amber-500 text-white px-4 py-2 rounded-md text-sm font-semibold transition-all shadow-lg shadow-amber-500/20 whitespace-nowrap"
                          >
                            Duyệt & Đăng tải
                          </button>
                        </div>
                      )}

                      {result.output_dir && (
                        <div className="text-sm">
                          <span className="text-slate-500">Output:</span>{' '}
                          <span className="text-slate-300 break-all font-mono text-xs">{result.output_dir}</span>
                        </div>
                      )}

                      {result.youtube_url && (
                        <div className="text-sm">
                          <span className="text-slate-500">YouTube:</span>{' '}
                          <a href={result.youtube_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
                            {result.youtube_url}
                          </a>
                        </div>
                      )}

                      {result.facebook_url && (
                        <div className="text-sm">
                          <span className="text-slate-500">Facebook:</span>{' '}
                          <a href={result.facebook_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
                            {result.facebook_url}
                          </a>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div>
                      <p className="text-red-400 font-semibold">✗ Lỗi xử lý</p>
                      <p className="text-sm text-slate-400 mt-2 font-mono">{result.error}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-lg bg-slate-800 border border-slate-700/50 p-8 text-center">
                  {jobId ? (
                    <div className="space-y-2">
                      <svg className="animate-spin h-8 w-8 text-indigo-400 mx-auto" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <p className="text-slate-400 text-sm">Đang xử lý...</p>
                    </div>
                  ) : (
                    <p className="text-slate-600 italic text-sm">
                      Kết quả sẽ xuất hiện ở đây sau khi pipeline hoàn thành.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 mt-12 py-6 px-4">
        <div className="max-w-6xl mx-auto text-center text-xs text-slate-600 space-y-1">
          <p>🔧 faster-whisper (ASR) · Local LLM (Ollama/vLLM) · Edge TTS · FFmpeg</p>
          <p>Cấu hình trong file <code className="text-slate-500">.env</code> · AUTO_PUBLISH=false là mặc định</p>
        </div>
      </footer>
    </div>
  );
}

export default App;

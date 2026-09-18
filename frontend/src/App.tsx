import { useState, useEffect } from 'react';
import PipelineForm from './PipelineForm';
import LogViewer from './LogViewer';

function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  // Optional: Poll for final status
  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/status/${jobId}`);
        const data = await res.json();
        if (data.status === 'completed' || data.status === 'failed') {
          setResult(data.result);
          clearInterval(interval);
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId]);

  return (
    <div className="min-h-screen bg-slate-900 py-12 px-4 sm:px-6 lg:px-8 font-sans text-slate-100">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
            🎬 AI Video Translation & Voice Cloning
          </h1>
          <p className="mt-3 max-w-2xl mx-auto text-xl text-slate-400 sm:mt-4">
            Tự động dịch và lồng tiếng Việt cho video YouTube, TikTok, Douyin
          </p>
          <p className="mt-2 max-w-2xl mx-auto text-sm text-slate-500">
            Local-first: audio và transcript được xử lý trên máy của bạn; xuất bản cần được duyệt riêng.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Left Panel - Input */}
          <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700 shadow-xl">
            <h2 className="text-2xl font-bold mb-6 text-indigo-400">📥 Input Configuration</h2>
            <PipelineForm onJobStarted={(id) => {
              setJobId(id);
              setResult(null);
            }} />
          </div>

          {/* Right Panel - Output */}
          <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700 shadow-xl flex flex-col">
            <h2 className="text-2xl font-bold mb-6 text-indigo-400">📊 Progress & Results</h2>
            
            <LogViewer jobId={jobId} />

            {/* Results Section */}
            <div className="mt-6">
              <h3 className="text-lg font-semibold mb-3">✅ Results</h3>
              {result ? (
                <div className={`p-4 rounded-md border ${result.success ? 'bg-green-500/10 border-green-500' : 'bg-red-500/10 border-red-500'}`}>
                  {result.success ? (
                    <div className="space-y-2">
                      <p className="text-green-400 font-medium">✓ PIPELINE COMPLETE</p>
                      {result.upload_pending && (
                        <p className="text-amber-300 text-sm">
                          Video đã được tạo và đang chờ duyệt; chưa đăng lên nền tảng.
                        </p>
                      )}
                      {result.output_dir && (
                        <p className="text-sm text-slate-300 break-all">
                          <span className="text-slate-400">Output:</span> {result.output_dir}
                        </p>
                      )}
                      {result.youtube_url && (
                        <p>
                          <span className="text-slate-400">YouTube:</span>{' '}
                          <a href={result.youtube_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
                            {result.youtube_url}
                          </a>
                        </p>
                      )}
                      {result.facebook_url && (
                        <p>
                          <span className="text-slate-400">Facebook:</span>{' '}
                          <a href={result.facebook_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
                            {result.facebook_url}
                          </a>
                        </p>
                      )}
                    </div>
                  ) : (
                    <div>
                      <p className="text-red-400 font-medium">✗ ERROR</p>
                      <p className="text-sm mt-1">{result.error}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-4 rounded-md bg-slate-800 border border-slate-700 text-slate-500 italic text-sm">
                  Kết quả xử lý sẽ xuất hiện ở đây.
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default App;

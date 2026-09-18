import React, { useState } from 'react';

interface PipelineFormProps {
  onJobStarted: (jobId: string) => void;
}

const PipelineForm: React.FC<PipelineFormProps> = ({ onJobStarted }) => {
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [voiceId, setVoiceId] = useState('vi-Female-1');
  const [bgMusic, setBgMusic] = useState('none');
  const [youtubeUpload, setYoutubeUpload] = useState(false);
  const [facebookUpload, setFacebookUpload] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url && !file) {
      setError('Please provide a Video URL or upload a File.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let local_video_path = null;

      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        const uploadRes = await fetch('http://localhost:8000/api/upload', {
          method: 'POST',
          body: formData,
        });
        if (!uploadRes.ok) throw new Error('File upload failed');
        const uploadData = await uploadRes.json();
        local_video_path = uploadData.local_video_path;
      }

      const response = await fetch('http://localhost:8000/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url || '',
          local_video_path,
          voice_id: voiceId,
          background_music: bgMusic,
          youtube_upload: youtubeUpload,
          facebook_upload: facebookUpload,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start pipeline');
      }

      const data = await response.json();
      onJobStarted(data.job_id);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-500 p-3 rounded-md text-sm">
          {error}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Video URL
        </label>
        <input
          type="url"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (e.target.value) setFile(null);
          }}
          placeholder="Paste YouTube, TikTok, or Douyin URL here..."
          className="w-full bg-slate-800 border border-slate-700 rounded-md py-2 px-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div className="flex items-center space-x-4">
        <div className="h-[1px] bg-slate-700 flex-1"></div>
        <span className="text-sm text-slate-500 uppercase">OR</span>
        <div className="h-[1px] bg-slate-700 flex-1"></div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Upload Video File
        </label>
        <input
          type="file"
          accept="video/*"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              setFile(e.target.files[0]);
              setUrl('');
            }
          }}
          className="w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 bg-slate-800 border border-slate-700 rounded-md"
        />
        {file && <p className="mt-2 text-xs text-indigo-400">Selected: {file.name}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Voice Selection (Giọng Việt)
        </label>
        <select
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 rounded-md py-2 px-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="vi-Female-1">vi-Female-1 (Nữ - HoaiMy)</option>
          <option value="vi-Male-1">vi-Male-1 (Nam - NamMinh)</option>
          <option value="default">default (Nữ)</option>
        </select>
        <p className="mt-1 text-xs text-slate-400">
          ASR và dịch chạy local mặc định. TTS hiện dùng Edge cho đến khi bạn cấu hình TTS tiếng Việt self-hosted.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Background Music
        </label>
        <div className="space-x-4">
          <label className="inline-flex items-center">
            <input
              type="radio"
              value="none"
              checked={bgMusic === 'none'}
              onChange={(e) => setBgMusic(e.target.value)}
              className="text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-700"
            />
            <span className="ml-2 text-sm text-slate-300">None</span>
          </label>
          <label className="inline-flex items-center">
            <input
              type="radio"
              value="duck"
              checked={bgMusic === 'duck'}
              onChange={(e) => setBgMusic(e.target.value)}
              className="text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-700"
            />
            <span className="ml-2 text-sm text-slate-300">Duck (-12dB)</span>
          </label>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Target Platforms
        </label>
        <div className="space-y-2">
          <label className="inline-flex items-center">
            <input
              type="checkbox"
              checked={youtubeUpload}
              onChange={(e) => setYoutubeUpload(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-700"
            />
            <span className="ml-2 text-sm text-slate-300">YouTube (OAuth2)</span>
          </label>
          <br/>
          <label className="inline-flex items-center">
            <input
              type="checkbox"
              checked={facebookUpload}
              onChange={(e) => setFacebookUpload(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-700"
            />
            <span className="ml-2 text-sm text-slate-300">Facebook (Graph API)</span>
          </label>
        </div>
        <p className="mt-2 text-xs text-amber-300">
          Video sẽ chỉ được tạo và chờ duyệt nếu AUTO_PUBLISH=false; mặc định không tự đăng.
        </p>
      </div>

      <button
        type="submit"
        disabled={loading}
        className={`w-full py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 focus:ring-offset-slate-900 ${
          loading ? 'opacity-75 cursor-not-allowed' : ''
        }`}
      >
        {loading ? 'Starting Pipeline...' : '▶ RUN PIPELINE'}
      </button>
    </form>
  );
};

export default PipelineForm;

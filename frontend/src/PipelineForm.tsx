import React, { useState, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '';

interface PipelineFormProps {
  onJobStarted: (jobId: string) => void;
}

export default function PipelineForm({ onJobStarted }: PipelineFormProps) {
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [voiceId, setVoiceId] = useState('vi-Female-1');
  const [bgMusic, setBgMusic] = useState('none');
  const [youtubeUpload, setYoutubeUpload] = useState(false);
  const [facebookUpload, setFacebookUpload] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url && !file) {
      setError('Vui lòng nhập URL video hoặc tải lên file.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let local_video_path: string | null = null;

      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        const uploadRes = await fetch(`${API_BASE}/api/upload`, {
          method: 'POST',
          body: formData,
        });
        if (!uploadRes.ok) throw new Error('Upload file thất bại');
        const uploadData = await uploadRes.json();
        local_video_path = uploadData.local_video_path;
      }

      const response = await fetch(`${API_BASE}/api/process`, {
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
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Khởi chạy pipeline thất bại');
      }

      const data = await response.json();
      onJobStarted(data.job_id);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith('video/')) {
      setFile(droppedFile);
      setUrl('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-3 rounded-lg text-sm fade-in">
          {error}
        </div>
      )}

      {/* URL Input */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1.5">
          🔗 Video URL
        </label>
        <input
          type="url"
          value={url}
          onChange={(e) => { setUrl(e.target.value); if (e.target.value) setFile(null); }}
          placeholder="Paste YouTube, TikTok, or Douyin URL..."
          className="w-full bg-slate-800/80 border border-slate-600 rounded-lg py-2.5 px-3.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
        />
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="h-px bg-slate-700 flex-1" />
        <span className="text-xs text-slate-500 uppercase tracking-wider">hoặc</span>
        <div className="h-px bg-slate-700 flex-1" />
      </div>

      {/* File Upload - Drag & Drop */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1.5">
          📁 Upload Video
        </label>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`
            w-full border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all
            ${dragOver
              ? 'border-indigo-400 bg-indigo-500/10'
              : 'border-slate-600 bg-slate-800/40 hover:border-slate-500 hover:bg-slate-800/60'}
          `}
        >
          {file ? (
            <p className="text-indigo-400 text-sm">📎 {file.name}</p>
          ) : (
            <div>
              <p className="text-slate-400 text-sm">Kéo thả video vào đây</p>
              <p className="text-slate-600 text-xs mt-1">hoặc click để chọn file</p>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) { setFile(e.target.files[0]); setUrl(''); }
            }}
          />
        </div>
      </div>

      {/* Voice Selection */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1.5">
          🎤 Giọng nói (Tiếng Việt)
        </label>
        <select
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          className="w-full bg-slate-800/80 border border-slate-600 rounded-lg py-2.5 px-3.5 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
        >
          <option value="vi-Female-1">vi-Female-1 (Nữ - HoaiMy)</option>
          <option value="vi-Male-1">vi-Male-1 (Nam - NamMinh)</option>
          <option value="default">default (Nữ)</option>
        </select>
        <p className="mt-1 text-xs text-slate-500">
          ASR và dịch chạy local. TTS dùng Edge TTS cho đến khi cấu hình TTS self-hosted.
        </p>
      </div>

      {/* Background Music */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1.5">
          🎵 Nhạc nền
        </label>
        <div className="flex gap-4">
          {[
            { value: 'none', label: 'Không' },
            { value: 'duck', label: 'Duck (-12dB)' },
          ].map((opt) => (
            <label key={opt.value} className="inline-flex items-center cursor-pointer">
              <input
                type="radio"
                value={opt.value}
                checked={bgMusic === opt.value}
                onChange={(e) => setBgMusic(e.target.value)}
                className="text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-600"
              />
              <span className="ml-2 text-sm text-slate-300">{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Target Platforms */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1.5">
          📤 Nền tảng đăng tải
        </label>
        <div className="space-y-2">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={youtubeUpload}
              onChange={(e) => setYoutubeUpload(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-600"
            />
            <span className="ml-2 text-sm text-slate-300">▶ YouTube (OAuth2)</span>
          </label>
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={facebookUpload}
              onChange={(e) => setFacebookUpload(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-600"
            />
            <span className="ml-2 text-sm text-slate-300">📘 Facebook (Graph API)</span>
          </label>
        </div>
        <p className="mt-2 text-xs text-amber-400/80">
          Video chỉ được tạo và chờ duyệt nếu AUTO_PUBLISH=false (mặc định).
        </p>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading}
        className={`
          w-full py-3 px-4 rounded-lg font-semibold text-white text-sm transition-all duration-200
          ${loading
            ? 'bg-indigo-700/60 cursor-not-allowed'
            : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40'}
        `}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Đang khởi chạy...
          </span>
        ) : (
          '▶ RUN PIPELINE'
        )}
      </button>
    </form>
  );
}

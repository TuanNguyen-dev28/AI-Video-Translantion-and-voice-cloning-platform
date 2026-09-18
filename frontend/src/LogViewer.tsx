import React, { useState, useEffect, useRef } from 'react';

interface LogViewerProps {
  jobId: string | null;
}

const LogViewer: React.FC<LogViewerProps> = ({ jobId }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!jobId) return;

    setLogs([]); // Reset logs for new job
    const ws = new WebSocket(`ws://localhost:8000/ws/logs/${jobId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const message = event.data;
      if (message.includes("DONE_PIPELINE")) {
        ws.close();
      } else {
        setLogs((prev) => [...prev, message]);
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [jobId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="bg-slate-800 rounded-lg p-4 h-96 overflow-y-auto border border-slate-700 shadow-inner">
      {logs.length === 0 ? (
        <div className="text-slate-400 italic">Ready to process...</div>
      ) : (
        <ul className="space-y-1">
          {logs.map((log, idx) => (
            <li key={idx} className="text-sm font-mono text-slate-300">
              {log}
            </li>
          ))}
          <div ref={bottomRef} />
        </ul>
      )}
    </div>
  );
};

export default LogViewer;

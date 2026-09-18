import { useState, useEffect, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '';

interface LogViewerProps {
  jobId: string | null;
  onLogUpdate: (logs: string[]) => void;
}

export default function LogViewer({ jobId, onLogUpdate }: LogViewerProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!jobId) return;

    setLogs([]);
    const wsBase = API_BASE.replace(/^http/, 'ws') || `ws://${window.location.host}`;
    const ws = new WebSocket(`${wsBase}/ws/logs/${jobId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const message = event.data as string;
      if (message.includes('DONE_PIPELINE')) {
        ws.close();
      } else {
        setLogs((prev) => {
          const next = [...prev, message];
          onLogUpdate(next);
          return next;
        });
      }
    };

    ws.onerror = () => {
      setLogs((prev) => [...prev, '**ERROR**: WebSocket connection failed']);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) ws.close();
    };
  }, [jobId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  function colorClass(log: string): string {
    if (log.includes('ERROR')) return 'text-red-400';
    if (log.includes('WARNING')) return 'text-amber-400';
    if (log.includes('DONE')) return 'text-green-400';
    if (log.includes('STEP') || log.includes('PRECHECK')) return 'text-cyan-300';
    return 'text-slate-400';
  }

  return (
    <div className="bg-slate-950 rounded-lg p-4 h-72 overflow-y-auto border border-slate-700/50 font-mono text-xs shadow-inner">
      {logs.length === 0 ? (
        <div className="text-slate-600 italic flex items-center justify-center h-full">
          {jobId ? 'Connecting...' : 'Logs will appear here when pipeline starts...'}
        </div>
      ) : (
        <ul className="space-y-0.5">
          {logs.map((log, idx) => (
            <li key={idx} className={`${colorClass(log)} leading-relaxed`}>
              <span className="text-slate-600 mr-2 select-none">{String(idx + 1).padStart(3, '0')}</span>
              {log}
            </li>
          ))}
          <div ref={bottomRef} />
        </ul>
      )}
    </div>
  );
}

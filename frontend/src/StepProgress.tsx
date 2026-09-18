const API_BASE = import.meta.env.VITE_API_URL || '';

interface StepInfo {
  label: string;
  key: string;
}

const STEPS: StepInfo[] = [
  { label: 'Download Video', key: 'STEP 1' },
  { label: 'Extract Audio', key: 'STEP 2' },
  { label: 'Background Music', key: 'STEP 2.5' },
  { label: 'ASR Transcription', key: 'STEP 3' },
  { label: 'Translation', key: 'STEP 4' },
  { label: 'TTS Generation', key: 'STEP 5' },
  { label: 'Audio Mixing', key: 'STEP 6' },
  { label: 'Video Composition', key: 'STEP 7' },
  { label: 'Metadata & Upload', key: 'STEP 8' },
];

type StepStatus = 'pending' | 'active' | 'completed' | 'error';

function getStepStatuses(logs: string[]): StepStatus[] {
  const statuses: StepStatus[] = STEPS.map(() => 'pending');
  let lastActiveIdx = -1;

  for (const log of logs) {
    // Find which step this log belongs to
    for (let i = 0; i < STEPS.length; i++) {
      if (log.includes(STEPS[i].key)) {
        // Mark all previous steps as completed
        for (let j = 0; j <= i - 1; j++) {
          if (statuses[j] !== 'error') statuses[j] = 'completed';
        }
        statuses[i] = 'active';
        lastActiveIdx = i;
        break;
      }
    }

    if (log.includes('ERROR')) {
      if (lastActiveIdx >= 0) statuses[lastActiveIdx] = 'error';
    }

    if (log.includes('DONE')) {
      for (let i = 0; i < statuses.length; i++) {
        if (statuses[i] === 'active') statuses[i] = 'completed';
      }
    }
  }

  return statuses;
}

interface StepProgressProps {
  logs: string[];
}

export default function StepProgress({ logs }: StepProgressProps) {
  const statuses = getStepStatuses(logs);

  return (
    <div className="space-y-1">
      {STEPS.map((step, idx) => {
        const status = statuses[idx];
        return (
          <div key={step.key} className="flex items-center gap-3 py-1.5">
            {/* Circle */}
            <div
              className={`
                w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-all duration-300
                ${status === 'pending' ? 'bg-slate-700 text-slate-500' : ''}
                ${status === 'active' ? 'bg-indigo-500 text-white pulse-dot ring-2 ring-indigo-400/50' : ''}
                ${status === 'completed' ? 'bg-green-500 text-white' : ''}
                ${status === 'error' ? 'bg-red-500 text-white' : ''}
              `}
            >
              {status === 'completed' ? '✓' : status === 'error' ? '✗' : idx + 1}
            </div>

            {/* Label */}
            <span
              className={`
                text-sm transition-colors duration-300
                ${status === 'pending' ? 'text-slate-500' : ''}
                ${status === 'active' ? 'text-white font-medium' : ''}
                ${status === 'completed' ? 'text-green-400' : ''}
                ${status === 'error' ? 'text-red-400' : ''}
              `}
            >
              {step.label}
            </span>

            {/* Active indicator */}
            {status === 'active' && (
              <span className="text-xs text-indigo-300 ml-auto">Processing...</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

export { API_BASE };

import { useJobSocket } from '../hooks/useJobSocket';

interface Props {
  jobId: string;
  onDone: () => void;
}

export default function ProgressPanel({ jobId, onDone }: Props) {
  const { events, stage, pct, error } = useJobSocket(jobId);

  const stageLabels: Record<string, string> = {
    downloading: 'Downloading',
    transcribing: 'Transcribing',
    analyzing: 'Analyzing',
    scoring: 'Scoring Moments',
    cutting: 'Selecting Clips',
    reframing: 'Auto-Reframe',
    rendering: 'Rendering Clips',
    subtitle: 'Adding Subtitles',
    assets: 'Generating Assets',
  };

  if (error) {
    return (
      <div className="p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
        <h3 className="font-semibold">Error</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="flex justify-between text-sm mb-1">
          <span>{stageLabels[stage] || stage}</span>
          <span>{Math.round(pct)}%</span>
        </div>
        <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <details className="text-sm text-neutral-400">
        <summary className="cursor-pointer mb-2">View Logs</summary>
        <div className="max-h-48 overflow-y-auto bg-neutral-950 p-3 rounded font-mono text-xs space-y-1">
          {events.slice(-50).map((e, i) => (
            <div key={i} className={`flex gap-2 ${e.type === 'log' && e.level === 'error' ? 'text-red-400' : ''}`}>
              <span className="text-neutral-500">[{e.type}]</span>
              <span>{'msg' in e ? e.msg : e.stage ? `${e.stage} ${e.status} (${e.pct.toFixed(1)}%)` : e.type === 'done' ? 'Done' : JSON.stringify(e)}</span>
            </div>
          ))}
        </div>
      </details>

      {pct === 100 && (
        <div className="p-3 bg-green-900/30 border border-green-700 rounded-lg text-green-300 text-center">
          Processing complete! <button onClick={onDone} className="ml-2 underline">Continue</button>
        </div>
      )}
    </div>
  );
}
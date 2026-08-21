import { useState } from 'react';
import { api, type JobCreate } from '../lib/api';

interface Props {
  onSubmit: (job: { id: string }) => void;
}

export default function JobForm({ onSubmit }: Props) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [prefs, setPrefs] = useState<Partial<JobCreate>>({
    max_clip_seconds: 60,
    max_clips: 8,
    whisper_model: 'base',
    use_cloud_model: false,
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!url.trim()) return;

    try {
      setLoading(true);
      const job = await api.createJob(url, prefs);
      onSubmit(job);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create job');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto space-y-4">
      <div className="space-y-2">
        <label className="block text-sm font-medium text-neutral-300">YouTube URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          className="w-full px-4 py-2 bg-neutral-900 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-white placeholder-neutral-500"
          required
        />
      </div>

      <details className="group">
        <summary className="cursor-pointer text-sm text-neutral-400 hover:text-neutral-200">
          Advanced Options
        </summary>
        <div className="mt-3 space-y-3 pl-2 border-l border-neutral-800">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm text-neutral-400 mb-1">Max Clip Seconds</label>
              <input
                type="number"
                min={10}
                max={180}
                value={prefs.max_clip_seconds}
                onChange={(e) => setPrefs({ ...prefs, max_clip_seconds: Number(e.target.value) })}
                className="w-full px-3 py-2 bg-neutral-900 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-neutral-400 mb-1">Max Clips</label>
              <input
                type="number"
                min={1}
                max={15}
                value={prefs.max_clips}
                onChange={(e) => setPrefs({ ...prefs, max_clips: Number(e.target.value) })}
                className="w-full px-3 py-2 bg-neutral-900 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm text-neutral-400 mb-1">Whisper Model</label>
            <select
              value={prefs.whisper_model}
              onChange={(e) => setPrefs({ ...prefs, whisper_model: e.target.value })}
              className="w-full px-3 py-2 bg-neutral-900 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value="tiny">tiny (fastest)</option>
              <option value="base">base (default)</option>
              <option value="small">small</option>
              <option value="medium">medium</option>
              <option value="large">large (slowest)</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input
              type="checkbox"
              checked={prefs.use_cloud_model}
              onChange={(e) => setPrefs({ ...prefs, use_cloud_model: e.target.checked })}
              className="h-4 w-4 rounded border-neutral-700 bg-neutral-900 text-blue-500 focus:ring-blue-500"
            />
            Use cloud model (stub)
          </label>
        </div>
      </details>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !url.trim()}
        className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium text-white transition-colors"
      >
        {loading ? 'Starting...' : 'Create Job'}
      </button>
    </form>
  );
}
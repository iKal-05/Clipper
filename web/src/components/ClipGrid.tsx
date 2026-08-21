import type { Clip } from '../lib/api';
import ClipCard from './ClipCard';

interface Props {
  clips: Clip[];
  selectedIds: string[];
  trims: Record<string, { start: number; end: number }>;
  onSelect: (clipId: string, selected: boolean) => void;
  onTrim: (clipId: string, start: number, end: number) => void;
  apiBase: string;
}

export default function ClipGrid({ clips, selectedIds, trims: _trims, onSelect, onTrim, apiBase }: Props) {
  if (clips.length === 0) {
    return (
      <div className="text-center py-12 text-neutral-500">
        <svg className="mx-auto h-12 w-12 text-neutral-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
        <p>No clips generated yet.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {clips.map((clip) => (
        <ClipCard
          key={clip.id}
          clip={clip}
          selected={selectedIds.includes(clip.id)}
          onSelect={onSelect}
          onTrim={onTrim}
          apiBase={apiBase}
        />
      ))}
    </div>
  );
}
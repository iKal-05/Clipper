import { useState } from 'react';
import ClipPlayer from './ClipPlayer';
import TrimHandles from './TrimHandles';
import type { Clip } from '../lib/api';

interface Props {
  clip: Clip;
  selected: boolean;
  onSelect: (clipId: string, selected: boolean) => void;
  onTrim: (clipId: string, start: number, end: number) => void;
  apiBase: string;
}

export default function ClipCard({ clip, selected, onSelect, onTrim, apiBase }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [trim, setTrim] = useState({ start: clip.start, end: clip.end });

  const videoUrl = `${apiBase}/api/clips/${clip.id}/video`;
  const thumbUrl = `${apiBase}/api/clips/${clip.id}/thumbnail`;

  function handleTrimChange(start: number, end: number) {
    setTrim({ start, end });
    onTrim(clip.id, start, end);
  }

  const momentLabel = clip.moment_labels[0] || 'Clip';

  return (
    <div className={`group relative bg-neutral-900 rounded-xl border overflow-hidden transition-all ${
      selected ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-neutral-700'
    }`}>
      {/* Checkbox overlay */}
      <label className="absolute top-2 left-2 z-10 flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={selected}
          onChange={(e) => onSelect(clip.id, e.target.checked)}
          className="h-5 w-5 rounded border-neutral-700 bg-neutral-900 text-blue-500 focus:ring-blue-500"
        />
        <span className="text-xs text-white bg-black/50 px-1.5 py-0.5 rounded">Select</span>
      </label>

      {/* Thumbnail / Player */}
      <div className="aspect-video relative">
        {expanded ? (
          <ClipPlayer videoUrl={videoUrl} thumbnailUrl={thumbUrl} duration={trim.end - trim.start} />
        ) : (
          <img
            src={thumbUrl}
            alt={clip.id}
            className="w-full h-full object-cover transition-opacity"
            onError={(e) => {
              e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 720 1280%22%3E%3Crect fill=%22%231a1a1a%22 width=%22720%22 height=%221280%22/%3E%3C/svg%3E';
              e.currentTarget.onerror = null;
            }}
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        {!expanded && (
          <button
            onClick={() => setExpanded(true)}
            className="absolute inset-0 flex items-center justify-center text-white/0 group-hover:text-white/100 transition-colors"
            aria-label="Play preview"
          >
            <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          </button>
        )}
        {expanded && (
          <button
            onClick={() => setExpanded(false)}
            className="absolute top-2 right-2 p-2 bg-black/50 rounded-full text-white hover:bg-black/70 transition-colors"
            aria-label="Close preview"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
          </button>
        )}
      </div>

      {/* Info bar */}
      <div className="p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full font-medium">
            {momentLabel}
          </span>
          <span className="text-xs text-neutral-500">Score: {clip.score.toFixed(1)}</span>
        </div>

        {/* Trim handles when expanded or selected */}
        {(expanded || selected) && (
          <TrimHandles
            videoUrl={videoUrl}
            start={trim.start}
            end={trim.end}
            duration={clip.duration}
            onChange={handleTrimChange}
          />
        )}

        <div className="flex justify-between text-xs text-neutral-500">
          <span>{Math.floor(clip.start / 60)}:{String(Math.floor(clip.start % 60)).padStart(2, '0')}</span>
          <span>{Math.floor(clip.duration)}s</span>
          <span>{Math.floor(clip.end / 60)}:{String(Math.floor(clip.end % 60)).padStart(2, '0')}</span>
        </div>
      </div>
    </div>
  );
}
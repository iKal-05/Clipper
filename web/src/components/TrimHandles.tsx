import { useRef, useState, useEffect } from 'react';

interface Props {
  videoUrl: string;
  start: number;
  end: number;
  duration: number;
  onChange: (start: number, end: number) => void;
}

export default function TrimHandles({ videoUrl, start, end, duration, onChange }: Props) {
  const [dragStart, setDragStart] = useState(false);
  const [dragEnd, setDragEnd] = useState(false);
  const [hoverPos, setHoverPos] = useState<number | null>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  function onMouseDownStart() { setDragStart(true); }
  function onMouseDownEnd() { setDragEnd(true); }

  function handleTrackMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setHoverPos(pct * duration);
  }

  function handleTrackMouseLeave() {
    setHoverPos(null);
  }

  useEffect(() => {
    function onMouseMove(e: MouseEvent) {
      if (!dragStart && !dragEnd) return;
      const rect = trackRef.current?.getBoundingClientRect();
      if (!rect) return;
      const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const time = pct * duration;
      if (dragStart) {
        const newStart = Math.min(time, end - 0.5);
        onChange(newStart, end);
      }
      if (dragEnd) {
        const newEnd = Math.max(time, start + 0.5);
        onChange(start, newEnd);
      }
    }
    function onMouseUp() { setDragStart(false); setDragEnd(false); }
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => { window.removeEventListener('mousemove', onMouseMove); window.removeEventListener('mouseup', onMouseUp); };
  }, [dragStart, dragEnd, start, end, duration, onChange]);

  function fmt(t: number) {
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60);
    const ms = Math.floor((t % 1) * 100);
    return `${m}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  }

  const startPct = (start / duration) * 100;
  const endPct = (end / duration) * 100;
  const widthPct = endPct - startPct;

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-neutral-400 mb-1">
        <span>Start: {fmt(start)}</span>
        <span>End: {fmt(end)}</span>
        <span>Dur: {fmt(end - start)}</span>
      </div>
      <div
        ref={trackRef}
        className="relative h-8 bg-neutral-800 rounded-lg overflow-hidden cursor-ew-resize"
        onMouseMove={handleTrackMouseMove}
        onMouseLeave={handleTrackMouseLeave}
      >
        <video ref={videoRef} src={videoUrl} muted preload="metadata" className="absolute inset-0 w-full h-full object-cover opacity-30" />
        <div className="absolute inset-0 h-full bg-gradient-to-r from-transparent via-neutral-900/50 to-transparent" />
        <div
          className="absolute top-0 bottom-0 bg-blue-500/40"
          style={{ left: `${startPct}%`, width: `${widthPct}%` }}
        />
        {/* Start handle */}
        <button
          onMouseDown={onMouseDownStart}
          className="absolute top-0 bottom-0 w-1 bg-blue-500 border-2 border-white shadow-lg transform -translate-x-1/2 z-10 focus:outline-none focus:ring-2 focus:ring-blue-400"
          style={{ left: `${startPct}%` }}
          aria-label="Trim start"
        />
        {/* End handle */}
        <button
          onMouseDown={onMouseDownEnd}
          className="absolute top-0 bottom-0 w-1 bg-blue-500 border-2 border-white shadow-lg transform translate-x-1/2 z-10 focus:outline-none focus:ring-2 focus:ring-blue-400"
          style={{ left: `${endPct}%` }}
          aria-label="Trim end"
        />
        {/* Hover preview */}
        {hoverPos !== null && (
          <div
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-black/80 text-white text-xs rounded whitespace-nowrap"
            style={{ left: `${(hoverPos / duration) * 100}%` }}
          >
            {fmt(hoverPos)}
          </div>
        )}
      </div>
      <div className="flex justify-between text-xs text-neutral-500 mt-1">
        <span>0:00</span>
        <span>{fmt(duration)}</span>
      </div>
    </div>
  );
}
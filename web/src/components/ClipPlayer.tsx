import { useRef, useState } from 'react';

interface Props {
  videoUrl: string;
  thumbnailUrl?: string;
  duration: number;
}

export default function ClipPlayer({ videoUrl, thumbnailUrl, duration }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [hoverTime, setHoverTime] = useState<number | null>(null);

  function togglePlay() {
    if (videoRef.current) {
      if (playing) videoRef.current.pause();
      else videoRef.current.play();
      setPlaying(!playing);
    }
  }

  function onTimeUpdate() {
    if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
  }

  function onMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = x / rect.width;
    setHoverTime(pct * duration);
  }

  function onMouseLeave() {
    setHoverTime(null);
  }

  function onClickSeek(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = x / rect.width;
    if (videoRef.current) videoRef.current.currentTime = pct * duration;
  }

  function fmt(t: number) {
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  return (
    <div className="relative w-full aspect-video bg-neutral-950 rounded-lg overflow-hidden">
      <video
        ref={videoRef}
        src={videoUrl}
        poster={thumbnailUrl}
        onTimeUpdate={onTimeUpdate}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        className="w-full h-full object-cover"
        preload="metadata"
      />
      <div
        className="absolute inset-0 flex items-center justify-center"
        onMouseMove={onMouseMove}
        onMouseLeave={onMouseLeave}
        onClick={onClickSeek}
      >
        {!playing && thumbnailUrl && (
          <img src={thumbnailUrl} alt="" className="w-full h-full object-cover" />
        )}
        <button
          className={`absolute p-3 rounded-full bg-black/50 text-white backdrop-blur transition-opacity ${
            playing ? 'opacity-0 pointer-events-none' : 'opacity-100'
          }`}
          onClick={(e) => { e.stopPropagation(); togglePlay(); }}
          aria-label={playing ? 'Pause' : 'Play'}
        >
          {playing ? (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
          ) : (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          )}
        </button>

        {hoverTime !== null && (
          <div className="absolute bottom-12 left-1/2 -translate-x-1/2 px-2 py-1 bg-black/80 text-white text-xs rounded pointer-events-none">
            {fmt(hoverTime)} / {fmt(duration)}
          </div>)
        }

        <div className="absolute bottom-0 left-0 right-0 h-2 bg-gradient-to-t from-black/60 to-transparent pointer-events-none">
          <div
            className="h-full bg-blue-500"
            style={{ width: `${(currentTime / duration) * 100}%` }}
          />
          {hoverTime !== null && (
            <div
              className="absolute top-0 w-0.5 h-full bg-white"
              style={{ left: `${(hoverTime / duration) * 100}%` }}
            />
          )}
        </div>
      </div>

      <div className="absolute bottom-2 left-2 right-2 flex justify-between text-xs text-white/80 px-1">
        <span>{fmt(currentTime)}</span>
        <span>{fmt(duration)}</span>
      </div>
    </div>
  );
}
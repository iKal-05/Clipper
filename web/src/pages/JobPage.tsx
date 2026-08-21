import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, type Job, type Clip, type Asset, type TrimSpan } from '../lib/api';
import ClipGrid from '../components/ClipGrid';
import AssetPanel from '../components/AssetPanel';

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [trims, setTrims] = useState<Record<string, { start: number; end: number }>>({});
  const [showAssets, setShowAssets] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    async function load() {
      try {
        setLoading(true);
        const [jobData, clipsData] = await Promise.all([
          api.getJob(id),
          api.listClips(id),
        ]);
        setJob(jobData);
        setClips(clipsData);
        // Initialize trims from clip boundaries
        const initialTrims: Record<string, { start: number; end: number }> = {};
        clipsData.forEach((c) => {
          initialTrims[c.id] = { start: c.start, end: c.end };
        });
        setTrims(initialTrims);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load job');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  function handleSelect(clipId: string, selected: boolean) {
    setSelectedIds((prev) => selected ? [...prev, clipId] : prev.filter((id) => id !== clipId));
  }

  function handleTrim(clipId: string, start: number, end: number) {
    setTrims((prev) => ({ ...prev, [clipId]: { start, end } }));
  }

  async function handleConfirm() {
    if (selectedIds.length === 0) return;
    try {
      const trimSpans: TrimSpan[] = selectedIds.map((id) => ({
        clip_id: id,
        start: trims[id]?.start ?? 0,
        end: trims[id]?.end ?? 0,
      }));
      await api.selectClips(id!, selectedIds, trimSpans);
      // Load assets
      const assetsData = await api.listAssets(id!);
      setAssets(assetsData);
      setShowAssets(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to confirm selection');
    }
  }

  function handleCopy(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(text);
    setTimeout(() => setCopied(null), 2000);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button onClick={() => navigate('/')} className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-500">
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <p className="text-neutral-500">Job not found</p>
      </div>
    );
  }

  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 pb-12">
      <header className="border-b border-neutral-800 px-4 py-4 sticky top-0 bg-neutral-950/95 backdrop-blur z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Job {job.id.slice(0, 8)}</h1>
            <p className="text-sm text-neutral-400">{job.url}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`px-2 py-1 text-xs rounded-full ${
              job.status === 'done' ? 'bg-green-500/20 text-green-400' :
              job.status === 'error' ? 'bg-red-500/20 text-red-400' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              {job.status}
            </span>
            {showAssets && assets.length > 0 && (
              <button
                onClick={() => setShowAssets(!showAssets)}
                className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 rounded-lg text-sm transition-colors"
              >
                {showAssets ? 'Hide Assets' : 'Show Assets'}
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {!showAssets ? (
          <>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-medium">Generated Clips ({clips.length})</h2>
              {selectedIds.length > 0 && (
                <button
                  onClick={handleConfirm}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium text-white transition-colors"
                >
                  Confirm Selection ({selectedIds.length})
                </button>
              )}
            </div>

            <ClipGrid
              clips={clips}
              selectedIds={selectedIds}
              trims={trims}
              onSelect={handleSelect}
              onTrim={handleTrim}
              apiBase={apiBase}
            />

            {clips.length > 0 && selectedIds.length === 0 && (
              <p className="text-center text-neutral-500 mt-4">
                Select clips to generate assets
              </p>
            )}
          </>
        ) : (
          <div className="space-y-6">
            <h2 className="text-lg font-medium">Assets ({assets.length})</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Asset list */}
              <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-2">
                {assets.map((asset) => (
                  <button
                    key={asset.clip_id}
                    onClick={() => setSelectedAsset(asset)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedAsset?.clip_id === asset.clip_id
                        ? 'border-blue-500 bg-blue-500/5'
                        : 'border-neutral-700 hover:border-neutral-600'
                    }`}
                  >
                    <div className="font-medium truncate">{asset.title}</div>
                    <div className="text-sm text-neutral-400 line-clamp-1">{asset.hook}</div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {asset.hashtags.slice(0, 3).map((t) => (
                        <span key={t} className="px-1.5 py-0.5 bg-blue-500/10 text-blue-400 text-xs rounded">#{t}</span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>

              {/* Asset detail */}
              {selectedAsset ? (
                <AssetPanel asset={selectedAsset} apiBase={apiBase} onCopy={handleCopy} />
              ) : (
                <div className="flex items-center justify-center h-[60vh] text-neutral-500">
                  Select an asset to view details
                </div>
              )}
            </div>

            {copied && (
              <div className="fixed bottom-4 right-4 bg-green-900/90 text-green-300 px-4 py-2 rounded-lg shadow-lg animate-fade-in">
                Copied!
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
import type { Asset } from '../lib/api';

interface Props {
  asset: Asset;
  apiBase: string;
  onCopy: (text: string) => void;
}

export default function AssetPanel({ asset, apiBase, onCopy }: Props) {
  const copy = (text: string) => { onCopy(text); };
  const thumbUrl = `${apiBase}/api/clips/${asset.clip_id}/thumbnail`;

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <img src={thumbUrl} alt="" className="w-32 h-32 object-cover rounded-lg border border-neutral-700"
          onError={(e) => {
            e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 720 1280%22%3E%3Crect fill=%22%231a1a1a%22 width=%22720%22 height=%221280%22/%3E%3C/svg%3E';
            e.currentTarget.onerror = null;
          }}
        />
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-white truncate">{asset.title}</h3>
          <p className="text-sm text-neutral-400 mt-1 line-clamp-2">{asset.hook}</p>
        </div>
      </div>

      <div className="space-y-4">
        <section>
          <h4 className="text-sm font-medium text-neutral-400 mb-2">Description</h4>
          <div className="flex gap-2">
            <textarea
              readOnly
              className="flex-1 px-3 py-2 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white resize-none h-24 font-mono"
              value={asset.description}
            />
            <button onClick={() => copy(asset.description)} className="px-3 py-2 bg-neutral-800 hover:bg-neutral-700 rounded-lg text-sm text-neutral-300 transition-colors">
              Copy
            </button>
          </div>
        </section>

        <section>
          <h4 className="text-sm font-medium text-neutral-400 mb-2">Hashtags</h4>
          <div className="flex flex-wrap gap-2">
            {asset.hashtags.map((tag) => (
              <span key={tag} className="px-2 py-1 bg-blue-500/10 text-blue-400 text-xs rounded-full border border-blue-500/20 flex items-center gap-1">
                #{tag}
                <button onClick={() => copy(`#${tag}`)} className="text-[10px] opacity-50 hover:opacity-100">Copy</button>
              </span>
            ))}
          </div>
        </section>

        <section>
          <h4 className="text-sm font-medium text-neutral-400 mb-2">Platform Tags</h4>
          <div className="flex flex-wrap gap-2">
            {asset.platform_tags.map((tag) => (
              <span key={tag} className="px-2 py-1 bg-neutral-800 text-neutral-300 text-xs rounded-full border border-neutral-700">{tag}</span>
            ))}
          </div>
        </section>

        <section>
          <h4 className="text-sm font-medium text-neutral-400 mb-2">Keywords</h4>
          <div className="flex flex-wrap gap-2">
            {asset.keywords.map((kw) => (
              <span key={kw} className="px-2 py-1 bg-green-500/10 text-green-400 text-xs rounded-full border border-green-500/20 flex items-center gap-1">
                {kw}
                <button onClick={() => copy(kw)} className="text-[10px] opacity-50 hover:opacity-100">Copy</button>
              </span>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
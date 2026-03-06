import { FormEvent, useState, useCallback } from "react";
import { searchImages, thumbUrl, AssetResult } from "./api";
import AssetDetailModal from "./components/AssetDetailModal";

const TOP_K_OPTIONS = [5, 10, 20, 50, 100, 200, 500, 1000];

function SkeletonGrid({ count }: { count: number }) {
  return (
    <div className="skeleton-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-card">
          <div className="skeleton-thumb" />
          <div className="skeleton-line short" />
          <div className="skeleton-line" />
        </div>
      ))}
    </div>
  );
}

function ResultCard({
  result,
  onClick,
}: {
  result: AssetResult;
  onClick: () => void;
}) {
  const [imgError, setImgError] = useState(false);
  const score = (result.score * 100).toFixed(1);

  return (
    <div
      className="card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      title={`${result.metadata.filename} — score ${score}%`}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick();
      }}
    >
      {imgError ? (
        <div className="card-thumb-placeholder">No preview</div>
      ) : (
        <img
          className="card-thumb"
          src={thumbUrl(result.asset_id)}
          alt={result.metadata.filename}
          loading="lazy"
          onError={() => setImgError(true)}
        />
      )}
      <div className="card-info">
        <div className="card-score">{score}% match</div>
        <div className="card-filename">{result.metadata.filename}</div>
      </div>
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(10);
  const [results, setResults] = useState<AssetResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [selectedResult, setSelectedResult] = useState<AssetResult | null>(null);

  const handleSearch = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();
      const trimmed = query.trim();
      if (!trimmed) return;

      setLoading(true);
      setError(null);

      try {
        const data = await searchImages(trimmed, topK);
        setResults(data);
        setLastQuery(trimmed);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search failed");
        setResults(null);
      } finally {
        setLoading(false);
      }
    },
    [query, topK]
  );

  const hasResults = results !== null && results.length > 0;
  const noResults = results !== null && results.length === 0;

  return (
    <>
      <header>
        <h1>Discord Image Caching & Search</h1>
        <p>Semantic image search across your Discord channels</p>
      </header>

      <form onSubmit={handleSearch}>
        <div className="search-bar">
          <input
            type="text"
            placeholder='Search images — e.g. "thinking", "chart", "meme"'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      <div className="controls">
        <label>
          Results:
          <select value={topK} onChange={(e) => setTopK(Number(e.target.value))}>
            {TOP_K_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        {hasResults && (
          <span className="result-count">
            {results.length} result{results.length !== 1 ? "s" : ""} for &ldquo;{lastQuery}&rdquo;
          </span>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading && <SkeletonGrid count={topK} />}

      {!loading && hasResults && (
        <div className="grid">
          {results.map((r) => (
            <ResultCard key={r.asset_id} result={r} onClick={() => setSelectedResult(r)} />
          ))}
        </div>
      )}

      {!loading && noResults && (
        <div className="grid">
          <div className="empty-state">
            <h2>No results found</h2>
            <p>Try a different search term, or index more channels.</p>
          </div>
        </div>
      )}

      <AssetDetailModal
        result={selectedResult}
        onClose={() => setSelectedResult(null)}
      />
    </>
  );
}

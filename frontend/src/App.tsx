import { FormEvent, useState, useCallback } from "react";
import { searchImages, thumbUrl, AssetResult } from "./api";
import AssetDetailModal from "./components/AssetDetailModal";

const TOP_K_STEPS = [1, 5, 10, 20, 100] as const;
type TopKOption = number | "ALL";

function buildTopKOptions(totalAvailable: number | null): TopKOption[] {
  if (totalAvailable === null) return [...TOP_K_STEPS, "ALL"];
  if (totalAvailable <= 0) return [1];
  return [...TOP_K_STEPS.filter((step) => step <= totalAvailable), "ALL"];
}

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
        <div className="card-score">
          {result.tag_match && <span className="card-tag-badge">tag</span>}
          {score}% match
        </div>
        <div className="card-filename">{result.metadata.filename}</div>
      </div>
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState<TopKOption>(10);
  const [results, setResults] = useState<AssetResult[] | null>(null);
  const [totalAvailable, setTotalAvailable] = useState<number | null>(null);
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
        const requestedTopK = topK === "ALL" ? null : topK;
        const data = await searchImages(trimmed, requestedTopK);
        const availableOptions = buildTopKOptions(data.total_available);
        if (!availableOptions.includes(topK)) {
          setTopK(availableOptions[availableOptions.length - 1]);
        }
        setResults(data.results);
        setTotalAvailable(data.total_available);
        setLastQuery(trimmed);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search failed");
        setResults(null);
        setTotalAvailable(null);
      } finally {
        setLoading(false);
      }
    },
    [query, topK]
  );

  const topKOptions = buildTopKOptions(totalAvailable);
  const selectValue = String(topK);
  const loadingCount = topK === "ALL" ? 20 : topK;
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
          <select
            value={selectValue}
            onChange={(e) => {
              const value = e.target.value;
              setTopK(value === "ALL" ? "ALL" : Number(value));
            }}
          >
            {topKOptions.map((option) => (
              <option key={String(option)} value={String(option)}>
                {option}
              </option>
            ))}
          </select>
        </label>

        {hasResults && (
          <span className="result-count">
            {results.length}
            {totalAvailable !== null ? ` of ${totalAvailable}` : ""} result
            {results.length !== 1 ? "s" : ""} for &ldquo;{lastQuery}&rdquo;
          </span>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading && <SkeletonGrid count={loadingCount} />}

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

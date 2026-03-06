export interface AssetResult {
  asset_id: string;
  score: number;
  thumb_url: string;
  jump_url: string;
  tags: string[];
  tag_match: boolean;
  metadata: {
    channel_id: string;
    author_id: string;
    created_at: string;
    filename: string;
    mime_type: string;
    width: number;
    height: number;
  };
}

export interface QueryFilters {
  guild_id?: string;
  channel_id?: string;
  author_id?: string;
}

export interface SearchResponse {
  results: AssetResult[];
  total_available: number;
}

const API_BASE = import.meta.env.VITE_API_URL ?? "";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

const headers: Record<string, string> = {
  "Content-Type": "application/json",
  ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
};

export async function searchImages(
  queryText: string,
  topK: number | null,
  filters: QueryFilters = {}
): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers,
    body: JSON.stringify({ query_text: queryText, top_k: topK, filters }),
  });

  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return (await res.json()) as SearchResponse;
}

export function thumbUrl(assetId: string): string {
  return `${API_BASE}/thumb/${assetId}`;
}

export interface AssetTagsResponse {
  asset_id: string;
  tags: string[];
}

export async function getAssetTags(assetId: string): Promise<AssetTagsResponse> {
  const res = await fetch(`${API_BASE}/assets/${assetId}/tags`, { headers });
  if (!res.ok) throw new Error(`Failed to load tags: ${res.statusText}`);
  return res.json();
}

export async function putAssetTags(
  assetId: string,
  tags: string[]
): Promise<AssetTagsResponse> {
  const res = await fetch(`${API_BASE}/assets/${assetId}/tags`, {
    method: "PUT",
    headers,
    body: JSON.stringify({ tags }),
  });
  if (!res.ok) throw new Error(`Failed to save tags: ${res.statusText}`);
  return res.json();
}

import { useEffect, useRef, useState, KeyboardEvent } from "react";
import { AssetResult, getAssetTags, putAssetTags, thumbUrl } from "../api";

type Status = "idle" | "loading" | "saving" | "error";

function normalizeTag(raw: string): string {
  return raw
    .replace(/^#+/, "")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();
}

function splitAndNormalize(input: string): string[] {
  return input
    .split(",")
    .map(normalizeTag)
    .filter(Boolean);
}

interface Props {
  result: AssetResult | null;
  onClose: () => void;
}

export default function AssetDetailModal({ result, onClose }: Props) {
  const [tags, setTags] = useState<string[]>([]);
  const [savedTags, setSavedTags] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch tags whenever the modal opens for a new asset
  useEffect(() => {
    if (!result) return;
    setStatus("loading");
    setTags([]);
    setSavedTags([]);
    setInput("");
    setErrorMsg("");

    getAssetTags(result.asset_id)
      .then(({ tags: fetched }) => {
        setTags(fetched);
        setSavedTags(fetched);
        setStatus("idle");
      })
      .catch(() => {
        setStatus("error");
        setErrorMsg("Failed to load tags.");
      });
  }, [result?.asset_id]);

  // Focus the tag input once loaded
  useEffect(() => {
    if (result && status === "idle") {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [result, status]);

  // Esc to close
  useEffect(() => {
    if (!result) return;
    const handler = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [result, onClose]);

  if (!result) return null;

  async function saveTags(newTags: string[]) {
    if (!result) return;
    setStatus("saving");
    setErrorMsg("");
    try {
      const { tags: confirmed } = await putAssetTags(result.asset_id, newTags);
      setTags(confirmed);
      setSavedTags(confirmed);
      setStatus("idle");
    } catch {
      setTags(savedTags);
      setStatus("error");
      setErrorMsg("Failed to save tags. Changes reverted.");
    }
  }

  function handleAdd() {
    const newTags = splitAndNormalize(input);
    if (!newTags.length) return;

    const merged = [...tags];
    for (const t of newTags) {
      if (!merged.includes(t)) merged.push(t);
    }
    setInput("");
    setTags(merged);
    saveTags(merged);
  }

  function handleRemove(tag: string) {
    const updated = tags.filter((t) => t !== tag);
    setTags(updated);
    saveTags(updated);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  }

  const isBusy = status === "loading" || status === "saving";

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Asset detail"
    >
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          ✕
        </button>

        <div className="modal-image-wrap">
          <img
            className="modal-image"
            src={thumbUrl(result.asset_id)}
            alt={result.metadata.filename}
          />
        </div>

        <div className="modal-body">
          <div className="modal-meta">
            <span className="modal-filename" title={result.metadata.filename}>
              {result.metadata.filename}
            </span>
            <a
              className="modal-jump"
              href={result.jump_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              View in Discord ↗
            </a>
          </div>

          {status === "error" && (
            <div className="modal-error">{errorMsg}</div>
          )}

          <div className="modal-tags-section">
            <div className="modal-tags-label">
              Tags
              {status === "saving" && (
                <span className="modal-status-indicator"> · Saving…</span>
              )}
              {status === "loading" && (
                <span className="modal-status-indicator"> · Loading…</span>
              )}
            </div>

            <div className="modal-chips">
              {tags.length === 0 && status !== "loading" && (
                <span className="modal-no-tags">No tags yet</span>
              )}
              {tags.map((tag) => (
                <span key={tag} className="chip">
                  {tag}
                  <button
                    className="chip-remove"
                    onClick={() => handleRemove(tag)}
                    disabled={isBusy}
                    aria-label={`Remove tag ${tag}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            <div className="modal-add-tag">
              <input
                ref={inputRef}
                type="text"
                className="modal-tag-input"
                placeholder="Add tag… Enter or comma-separate multiple"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isBusy}
              />
              <button
                className="modal-add-btn"
                onClick={handleAdd}
                disabled={isBusy || !input.trim()}
              >
                Add
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import axios from "axios";
import FormData from "form-data";
import { config } from "./config";

const client = axios.create({
  baseURL: config.backendUrl,
  headers: { "X-API-Key": config.backendApiKey },
});

export interface IngestPayload {
  guild_id: string;
  channel_id: string;
  message_id: string;
  attachment_id: string;
  filename: string;
  author_id: string;
  created_at: string;
  imageBuffer: Buffer;
  content_type: string;
}

export async function ingestImage(payload: IngestPayload): Promise<void> {
  const form = new FormData();
  form.append("guild_id", payload.guild_id);
  form.append("channel_id", payload.channel_id);
  form.append("message_id", payload.message_id);
  form.append("attachment_id", payload.attachment_id);
  form.append("filename", payload.filename);
  form.append("author_id", payload.author_id);
  form.append("created_at", payload.created_at);
  form.append("image", payload.imageBuffer, {
    filename: payload.filename,
    contentType: payload.content_type,
  });

  await client.post("/ingest/discord", form, {
    headers: form.getHeaders(),
    maxContentLength: Infinity,
    maxBodyLength: Infinity,
  });
}

export async function setChannelIndexing(
  guildId: string,
  channelId: string,
  enabled: boolean,
  adminId: string
): Promise<void> {
  await client.post("/admin/channel", {
    guild_id: guildId,
    channel_id: channelId,
    enabled,
    admin_id: adminId,
  });
}

export async function isChannelIndexed(guildId: string, channelId: string): Promise<boolean> {
  try {
    const res = await client.get(`/admin/channel/${guildId}/${channelId}`);
    return res.data.enabled === true;
  } catch {
    return false;
  }
}

export async function reindexChannel(
  guildId: string,
  channelId: string,
  limit: number
): Promise<{ queued: number }> {
  const res = await client.post("/admin/reindex", { guild_id: guildId, channel_id: channelId, limit });
  return res.data;
}

export async function deleteByChannel(guildId: string, channelId: string): Promise<void> {
  await client.delete(`/admin/assets`, { data: { guild_id: guildId, channel_id: channelId } });
}

export async function deleteByMessage(guildId: string, messageId: string): Promise<void> {
  await client.delete(`/admin/assets`, { data: { guild_id: guildId, message_id: messageId } });
}

export async function health(): Promise<boolean> {
  try {
    const res = await client.get("/health");
    return res.data.status === "ok";
  } catch {
    return false;
  }
}

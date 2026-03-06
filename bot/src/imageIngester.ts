import axios from "axios";
import { Attachment, Message } from "discord.js";
import { ingestImage } from "./backendClient";

const SUPPORTED_MIME = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/gif",
]);

const SUPPORTED_EXT = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"]);

function isSupportedAttachment(attachment: Attachment): boolean {
  if (attachment.contentType && SUPPORTED_MIME.has(attachment.contentType)) return true;
  const lower = attachment.name.toLowerCase();
  return SUPPORTED_EXT.has(lower.slice(lower.lastIndexOf(".")));
}

export async function processMessage(message: Message): Promise<void> {
  if (!message.guild) return;

  const imageAttachments = message.attachments.filter(isSupportedAttachment);
  if (imageAttachments.size === 0) return;

  for (const [, attachment] of imageAttachments) {
    try {
      const response = await axios.get<ArrayBuffer>(attachment.url, {
        responseType: "arraybuffer",
        timeout: 30_000,
      });

      const buffer = Buffer.from(response.data);
      const contentType = attachment.contentType ?? "image/jpeg";

      await ingestImage({
        guild_id: message.guild.id,
        channel_id: message.channel.id,
        message_id: message.id,
        attachment_id: attachment.id,
        filename: attachment.name,
        author_id: message.author.id,
        created_at: message.createdAt.toISOString(),
        imageBuffer: buffer,
        content_type: contentType,
      });

      console.log(`[ingest] Indexed ${attachment.name} from msg ${message.id}`);
    } catch (err) {
      console.error(`[ingest] Failed to ingest attachment ${attachment.id}:`, err);
    }
  }
}

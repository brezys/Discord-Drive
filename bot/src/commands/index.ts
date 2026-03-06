import {
  ChatInputCommandInteraction,
  REST,
  Routes,
  SlashCommandBuilder,
  PermissionFlagsBits,
  TextChannel,
  ChannelType,
} from "discord.js";
import { config } from "../config";
import {
  setChannelIndexing,
  reindexChannel,
  deleteByChannel,
  deleteByMessage,
} from "../backendClient";
import { processMessage } from "../imageIngester";

export const commandDefinitions = [
  new SlashCommandBuilder()
    .setName("index")
    .setDescription("Manage image indexing for channels")
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addSubcommand((sub) =>
      sub
        .setName("enable")
        .setDescription("Enable image indexing for a channel")
        .addChannelOption((opt) =>
          opt.setName("channel").setDescription("Channel to index").setRequired(true)
        )
    )
    .addSubcommand((sub) =>
      sub
        .setName("disable")
        .setDescription("Disable image indexing for a channel")
        .addChannelOption((opt) =>
          opt.setName("channel").setDescription("Channel to disable").setRequired(true)
        )
    ),

  new SlashCommandBuilder()
    .setName("reindex")
    .setDescription("Backfill recent images from a channel")
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addChannelOption((opt) =>
      opt.setName("channel").setDescription("Channel to reindex").setRequired(true)
    )
    .addIntegerOption((opt) =>
      opt
        .setName("limit")
        .setDescription("Max messages to scan (default 500, max 5000)")
        .setMinValue(1)
        .setMaxValue(5000)
    ),

  new SlashCommandBuilder()
    .setName("delete-indexed")
    .setDescription("Delete indexed data")
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addSubcommand((sub) =>
      sub
        .setName("channel")
        .setDescription("Delete all indexed images for a channel")
        .addChannelOption((opt) =>
          opt.setName("channel").setDescription("Channel").setRequired(true)
        )
    )
    .addSubcommand((sub) =>
      sub
        .setName("message")
        .setDescription("Delete indexed images from a specific message ID")
        .addStringOption((opt) =>
          opt.setName("message_id").setDescription("Discord message ID").setRequired(true)
        )
    ),

  new SlashCommandBuilder()
    .setName("imgsearch")
    .setDescription("Search indexed images by text")
    .addStringOption((opt) =>
      opt.setName("query").setDescription("Search query").setRequired(true)
    )
    .addIntegerOption((opt) =>
      opt.setName("k").setDescription("Number of results (default 5)").setMinValue(1).setMaxValue(20)
    ),
].map((cmd) => cmd.toJSON());

export async function registerCommands(guildId?: string): Promise<void> {
  const rest = new REST().setToken(config.discordToken);
  if (guildId) {
    await rest.put(Routes.applicationGuildCommands(config.applicationId, guildId), {
      body: commandDefinitions,
    });
    console.log(`[commands] Registered guild commands for ${guildId}`);
  } else {
    await rest.put(Routes.applicationCommands(config.applicationId), {
      body: commandDefinitions,
    });
    console.log("[commands] Registered global commands");
  }
}

export async function handleCommand(interaction: ChatInputCommandInteraction): Promise<void> {
  const { commandName, guildId } = interaction;
  if (!guildId) {
    await interaction.reply({ content: "Commands only work in servers.", ephemeral: true });
    return;
  }

  if (commandName === "index") {
    const sub = interaction.options.getSubcommand();
    const channel = interaction.options.getChannel("channel", true);
    const enabled = sub === "enable";

    await setChannelIndexing(guildId, channel.id, enabled, interaction.user.id);
    await interaction.reply({
      content: `Indexing ${enabled ? "enabled" : "disabled"} for <#${channel.id}>.`,
      ephemeral: true,
    });
  } else if (commandName === "reindex") {
    const channel = interaction.options.getChannel("channel", true);
    const limit = interaction.options.getInteger("limit") ?? 500;

    await interaction.deferReply({ ephemeral: true });

    // Fetch messages from Discord and forward to backend
    const discordChannel = await interaction.client.channels.fetch(channel.id);
    if (!discordChannel || discordChannel.type !== ChannelType.GuildText) {
      await interaction.editReply("That channel is not a text channel.");
      return;
    }

    const textChannel = discordChannel as TextChannel;
    let count = 0;
    let lastId: string | undefined;
    const batchSize = 100;

    while (count < limit) {
      const toFetch = Math.min(batchSize, limit - count);
      const messages = await textChannel.messages.fetch({
        limit: toFetch,
        ...(lastId ? { before: lastId } : {}),
      });

      if (messages.size === 0) break;

      for (const [, msg] of messages) {
        await processMessage(msg);
        lastId = msg.id;
      }

      count += messages.size;
      if (messages.size < toFetch) break;
    }

    await interaction.editReply(`Reindex complete. Scanned ${count} messages from <#${channel.id}>.`);
  } else if (commandName === "delete-indexed") {
    const sub = interaction.options.getSubcommand();
    if (sub === "channel") {
      const channel = interaction.options.getChannel("channel", true);
      await deleteByChannel(guildId, channel.id);
      await interaction.reply({
        content: `Deleted all indexed images for <#${channel.id}>.`,
        ephemeral: true,
      });
    } else if (sub === "message") {
      const messageId = interaction.options.getString("message_id", true);
      await deleteByMessage(guildId, messageId);
      await interaction.reply({
        content: `Deleted indexed images for message \`${messageId}\`.`,
        ephemeral: true,
      });
    }
  } else if (commandName === "imgsearch") {
    const query = interaction.options.getString("query", true);
    const k = interaction.options.getInteger("k") ?? 5;

    await interaction.deferReply({ ephemeral: true });

    try {
      const backendClient = (await import("axios")).default.create({
        baseURL: config.backendUrl,
        headers: { "X-API-Key": config.backendApiKey },
      });

      const res = await backendClient.post("/query", {
        query_text: query,
        top_k: k,
        filters: { guild_id: guildId },
      });

      const results: Array<{
        asset_id: string;
        score: number;
        thumb_url: string;
        jump_url: string;
        metadata: { author_id: string; created_at: string; channel_id: string };
      }> = res.data.results;

      if (results.length === 0) {
        await interaction.editReply(`No results found for **${query}**.`);
        return;
      }

      const lines = results.map(
        (r, i) =>
          `**${i + 1}.** [Jump to message](${r.jump_url}) — score: ${r.score.toFixed(3)}`
      );
      await interaction.editReply(
        `**Results for "${query}":**\n${lines.join("\n")}`
      );
    } catch (err) {
      console.error("[imgsearch] Error:", err);
      await interaction.editReply("Search failed. Please try again.");
    }
  }
}

import {
  Client,
  GatewayIntentBits,
  Events,
  ChatInputCommandInteraction,
  Message,
  Interaction,
} from "discord.js";
import { config } from "./config";
import { processMessage } from "./imageIngester";
import { isChannelIndexed } from "./backendClient";
import { registerCommands, handleCommand } from "./commands";

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

client.once(Events.ClientReady, async (readyClient: Client<true>) => {
  console.log(`[bot] Logged in as ${readyClient.user.tag}`);

  // Register slash commands to all guilds the bot is in
  for (const [guildId] of readyClient.guilds.cache) {
    try {
      await registerCommands(guildId);
    } catch (err) {
      console.error(`[bot] Failed to register commands for guild ${guildId}:`, err);
    }
  }
});

client.on(Events.MessageCreate, async (message: Message) => {
  if (message.author.bot) return;
  if (!message.guild) return;
  if (message.attachments.size === 0) return;

  const indexed = await isChannelIndexed(message.guild.id, message.channel.id);
  if (!indexed) return;

  await processMessage(message);
});

client.on(Events.InteractionCreate, async (interaction: Interaction) => {
  if (!interaction.isChatInputCommand()) return;
  try {
    await handleCommand(interaction as ChatInputCommandInteraction);
  } catch (err) {
    console.error("[bot] Command error:", err);
    if (interaction.replied || interaction.deferred) {
      await interaction.editReply("An error occurred.");
    } else {
      await interaction.reply({ content: "An error occurred.", ephemeral: true });
    }
  }
});

client.login(config.discordToken);

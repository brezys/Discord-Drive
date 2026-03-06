import "dotenv/config";

function required(name: string): string {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

export const config = {
  discordToken: required("DISCORD_TOKEN"),
  applicationId: required("DISCORD_APPLICATION_ID"),
  backendUrl: process.env.BACKEND_URL ?? "http://localhost:8000",
  backendApiKey: required("BACKEND_API_KEY"),
};

"""
Discord Image Role Bot
======================
SETUP INSTRUCTIONS:
1. Install dependencies:
   pip install discord.py

2. Paste your bot token where indicated below (BOT_TOKEN variable).

3. Run the bot:
   python bot.py

4. In Discord, use /start role_id:<role_id> channel_id:<channel_id> to begin scanning.

HOW TO GET IDs:
- Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
- Right-click a channel → Copy ID
- Right-click a role → Copy ID
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# ─────────────────────────────────────────────
#  PASTE YOUR BOT TOKEN HERE
# ─────────────────────────────────────────────
BOT_TOKEN = "MTQ3MzUyMDg0MDYwNzAxMDkxMA.Gx6wH1.Q3MzlWbY4sExlAVEEQFeKWQCzW4XJBJ-HSQH14"
# ─────────────────────────────────────────────

DATA_FILE = "data.json"
SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "gif", "webp"}
IMAGES_REQUIRED = 5


# ── Data persistence ──────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "scanning": False,
        "channel_id": None,
        "role_id": None,
        "counts": {}          # { "user_id": image_count }
    }


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Bot setup ─────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
data = load_data()


# ── Helpers ───────────────────────────────────

def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator


def count_images(message: discord.Message) -> int:
    """Count only image attachments in a message."""
    return sum(
        1 for a in message.attachments
        if a.filename.rsplit(".", 1)[-1].lower() in SUPPORTED_FORMATS
    )


# ── Events ────────────────────────────────────

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Slash commands synced.")


@bot.event
async def on_message(message: discord.Message):
    # Ignore bots
    if message.author.bot:
        return

    # Only process if scanning is active and message is in the watched channel
    if not data["scanning"]:
        return
    if data["channel_id"] is None:
        return
    if message.channel.id != data["channel_id"]:
        return

    image_count = count_images(message)
    if image_count == 0:
        return

    user_id = str(message.author.id)
    data["counts"][user_id] = data["counts"].get(user_id, 0) + image_count
    save_data(data)

    # Check if user has reached the threshold
    if data["counts"][user_id] >= IMAGES_REQUIRED and data["role_id"]:
        guild = message.guild
        role = guild.get_role(data["role_id"])
        member = message.author

        if role and role not in member.roles:
            try:
                await member.add_roles(role)
                await message.channel.send(
                    f"{member.mention} has earned the role!"
                )
            except discord.Forbidden:
                print(f"Missing permissions to assign role to {member}.")


# ── Slash commands ────────────────────────────

@bot.tree.command(name="start", description="Start image scanning (Admin only)")
@app_commands.describe(
    role_id="ID of the role to assign",
    channel_id="ID of the channel to monitor"
)
async def start(interaction: discord.Interaction, role_id: str, channel_id: str):
    if not is_admin(interaction):
        await interaction.response.send_message("You need administrator permissions.", ephemeral=True)
        return

    try:
        data["role_id"] = int(role_id)
        data["channel_id"] = int(channel_id)
        data["scanning"] = True
        save_data(data)
        await interaction.response.send_message("Scanning started.")
    except ValueError:
        await interaction.response.send_message("Invalid role_id or channel_id. Please provide numeric IDs.", ephemeral=True)


@bot.tree.command(name="stop", description="Stop image scanning (Admin only)")
async def stop(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("You need administrator permissions.", ephemeral=True)
        return

    data["scanning"] = False
    save_data(data)
    await interaction.response.send_message("Scanning stopped.")


@bot.tree.command(name="check", description="Check current bot status")
async def check(interaction: discord.Interaction):
    status = "ON" if data["scanning"] else "OFF"

    channel_mention = "Not set"
    if data["channel_id"]:
        ch = interaction.guild.get_channel(data["channel_id"])
        channel_mention = ch.mention if ch else f"<#{data['channel_id']}>"

    role_name = "Not set"
    if data["role_id"]:
        role = interaction.guild.get_role(data["role_id"])
        role_name = role.name if role else str(data["role_id"])

    await interaction.response.send_message(
        f"**Status:** {status}\n"
        f"**Channel:** {channel_mention}\n"
        f"**Role:** {role_name}"
    )


# ── Run ───────────────────────────────────────

bot.run(BOT_TOKEN)

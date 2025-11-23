import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from flask import Flask
import threading
import os

# -----------------------------
# FLASK SERVER FOR KOYEB HEALTHCHECK
# -----------------------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

def start_webserver():
    thread = threading.Thread(target=run_flask)
    thread.daemon = True
    thread.start()

# -----------------------------
# DISCORD BOT SETUP
# -----------------------------

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# -----------------------------
# ON READY
# -----------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await tree.sync()
    print("Slash commands synced!")

# -----------------------------
# SLASH COMMANDS
# -----------------------------

@tree.command(name="ping", description="Check bot latency.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")

@tree.command(name="timeout", description="Timeout a user.")
@app_commands.describe(member="The user to timeout", minutes="Duration in minutes")
@commands.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int):
    try:
        duration = discord.utils.utcnow() + discord.utils.timedelta(minutes=minutes)
        await member.timeout(duration)
        await interaction.response.send_message(f"{member.mention} has been timed out for {minutes} minutes.")
    except:
        await interaction.response.send_message("Error applying timeout.", ephemeral=True)

@tree.command(name="untimeout", description="Remove timeout from a user.")
@app_commands.describe(member="The user to remove timeout from")
@commands.has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout(None)
        await interaction.response.send_message(f"Timeout removed for {member.mention}.")
    except:
        await interaction.response.send_message("Error removing timeout.", ephemeral=True)

@tree.command(name="ban", description="Ban a user.")
@app_commands.describe(member="User to ban", reason="Reason for ban")
@commands.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member.mention} has been banned. Reason: {reason}")
    except:
        await interaction.response.send_message("Error banning user.", ephemeral=True)

@tree.command(name="unban", description="Unban a user.")
@app_commands.describe(user_id="ID of banned user")
@commands.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: int):
    user = await bot.fetch_user(user_id)
    try:
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"Unbanned {user.name}.")
    except:
        await interaction.response.send_message("Error unbanning user.", ephemeral=True)

# -----------------------------
# START EVERYTHING
# -----------------------------

if __name__ == "__main__":
    start_webserver()
    bot.run(TOKEN)

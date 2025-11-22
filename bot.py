import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import json
import asyncio
from flask import Flask, jsonify, request
from threading import Thread
import time
import os

# ==================== CONFIGURATION ====================

TOKEN = os.getenv('DISCORD_BOT_TOKEN', 'My token')
ALLOWED_ROLES = ['Admin', 'Moderator', 'Head-Admin']

commands_queue = []
completed_commands = []

# ==================== FLASK WEB SERVER ====================

app = Flask(__name__)

@app.route('/commands.json', methods=['GET'])
def get_commands():
    return jsonify(commands_queue)

@app.route('/complete', methods=['POST'])
def complete_command():
    global commands_queue
    data = request.json
    cmd_id = data.get('id')
    success = data.get('success')
    message = data.get('message')
    
    commands_queue = [c for c in commands_queue if c['id'] != cmd_id]
    
    completed_commands.append({
        'id': cmd_id,
        'success': success,
        'message': message,
        'timestamp': time.time()
    })
    
    return jsonify({'status': 'ok'})


# ==================== NEW ENDPOINT FOR PLUGIN → DISCORD WEBHOOK ====================

@app.route('/webhook', methods=['POST'])
def forward_webhook():
    """CS sends messages here -> bot forwards to actual Discord webhook"""
    import requests
    data = request.json

    DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1441541218814398507/PHzwpDM3S6GmBGPAcSNSrQOjXRLlv7dZBiE3MOjSceai3pQpcogSEdD1t7vDM2FaDIcP"  # <--- ТУК СЛАГАШ ИСТИНСКИЯ WEBHOOK

    msg = data.get("msg", "")

    # Forward to actual Discord webhook
    requests.post(DISCORD_WEBHOOK, json={"content": msg})

    return jsonify({"status": "ok"})


# ===========================================================================

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'status': 'online',
        'queue_size': len(commands_queue),
        'completed': len(completed_commands)
    })

def run_flask():
    app.run(host='0.0.0.0', port=27041)

# ==================== DISCORD BOT ====================

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ==================== BUTTON VIEWS ====================

class TimeSelectView(View):
    def __init__(self, action, steamid, player_name, admin):
        super().__init__(timeout=60)
        self.action = action
        self.steamid = steamid
        self.player_name = player_name
        self.admin = admin
    
    @discord.ui.button(label="5 min", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def time_5min(self, interaction: discord.Interaction, button):
        await self.show_reason_modal(interaction, 5)
    
    @discord.ui.button(label="30 min", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def time_30min(self, interaction, button):
        await self.show_reason_modal(interaction, 30)
    
    @discord.ui.button(label="60 min", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def time_60min(self, interaction, button):
        await self.show_reason_modal(interaction, 60)
    
    @discord.ui.button(label="1 Day", style=discord.ButtonStyle.primary, emoji="📅")
    async def time_1day(self, interaction, button):
        await self.show_reason_modal(interaction, 1440)
    
    @discord.ui.button(label="Permanent", style=discord.ButtonStyle.danger, emoji="♾️")
    async def time_permanent(self, interaction, button):
        await self.show_reason_modal(interaction, 0)
    
    async def show_reason_modal(self, interaction, time_minutes):
        modal = ReasonModal(self.action, self.steamid, self.player_name, self.admin, time_minutes)
        await interaction.response.send_modal(modal)

class DamageSelectView(View):
    def __init__(self, steamid, player_name, admin):
        super().__init__(timeout=60)
        self.steamid = steamid
        self.player_name = player_name
        self.admin = admin
    
    @discord.ui.button(label="5 HP", style=discord.ButtonStyle.secondary)
    async def damage_5(self, interaction, button):
        await self.execute_slap(interaction, 5)
    
    @discord.ui.button(label="10 HP", style=discord.ButtonStyle.secondary)
    async def damage_10(self, interaction, button):
        await self.execute_slap(interaction, 10)
    
    @discord.ui.button(label="20 HP", style=discord.ButtonStyle.primary)
    async def damage_20(self, interaction, button):
        await self.execute_slap(interaction, 20)
    
    @discord.ui.button(label="50 HP", style=discord.ButtonStyle.danger)
    async def damage_50(self, interaction, button):
        await self.execute_slap(interaction, 50)
    
    async def execute_slap(self, interaction, damage):
        cmd_id = f"slap_{self.steamid}_{int(time.time())}"
        
        command = {
            'id': cmd_id,
            'cmd': 'slap',
            'target': self.steamid,
            'admin': str(interaction.user),
            'damage': damage,
            'timestamp': time.time()
        }
        
        commands_queue.append(command)
        
        await interaction.response.send_message(
            f"👋 **Slap command sent!**\nPlayer: {self.player_name}\nDamage: {damage} HP\n\n⏳ Wait...",
            ephemeral=True
        )
        
        await asyncio.sleep(6)
        result = next((c for c in completed_commands if c['id'] == cmd_id), None)
        if result:
            await interaction.followup.send(f"✅ {result['message']}", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Command not executed", ephemeral=True)

# ==================== MODALS ====================

class ReasonModal(Modal, title="Admin Action"):
    reason = TextInput(label="Reason", placeholder="Enter reason...", required=True, max_length=128)
    
    def __init__(self, action, steamid, player_name, admin, time_minutes=0):
        super().__init__()
        self.action = action
        self.steamid = steamid
        self.player_name = player_name
        self.admin = admin
        self.time_minutes = time_minutes
    
    async def on_submit(self, interaction):
        cmd_id = f"{self.action}_{self.steamid}_{int(time.time())}"
        
        command = {
            'id': cmd_id,
            'cmd': self.action,
            'target': self.steamid,
            'admin': str(interaction.user),
            'reason': str(self.reason),
            'time': self.time_minutes,
            'timestamp': time.time()
        }
        
        commands_queue.append(command)
        
        time_str = f"{self.time_minutes} min" if self.time_minutes > 0 else "Permanent"
        await interaction.response.send_message(
            f"✅ **{self.action.upper()} sent!**\nPlayer: {self.player_name}\nTime: {time_str}",
            ephemeral=True
        )
        
        await asyncio.sleep(6)
        result = next((c for c in completed_commands if c['id'] == cmd_id), None)
        if result:
            await interaction.followup.send(f"✔ {result['message']}", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Timeout", ephemeral=True)

class KickReasonModal(Modal, title="Kick Player"):
    reason = TextInput(label="Kick reason", placeholder="Enter reason...", required=True, max_length=128)
    
    def __init__(self, steamid, player_name, admin):
        super().__init__()
        self.steamid = steamid
        self.player_name = player_name
        self.admin = admin
    
    async def on_submit(self, interaction):
        cmd_id = f"kick_{self.steamid}_{int(time.time())}"
        
        command = {
            'id': cmd_id,
            'cmd': 'kick',
            'target': self.steamid,
            'admin': str(interaction.user),
            'reason': str(self.reason),
            'timestamp': time.time()
        }
        
        commands_queue.append(command)
        
        await interaction.response.send_message(
            f"👢 Kick sent for {self.player_name}",
            ephemeral=True
        )
        
        await asyncio.sleep(6)
        result = next((c for c in completed_commands if c['id'] == cmd_id), None)
        if result:
            await interaction.followup.send(result['message'], ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Timeout", ephemeral=True)

# ==================== BUTTON HANDLER ====================

@client.event
async def on_interaction(interaction):
    if interaction.type != discord.InteractionType.component:
        return
    
    if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return
    
    custom_id = interaction.data['custom_id']
    
    parts = custom_id.split('_', 1)
    if len(parts) != 2:
        return
    
    action, steamid = parts
    player_name = "Unknown"

    if interaction.message.embeds:
        try:
            desc = interaction.message.embeds[0].description
            player_name = desc.split('[ADMIN:')[0].split('] ')[1].split(' ')[0]
        except:
            pass
    
    if action == 'gag':
        await interaction.response.send_message(
            f"🔇 Gag {player_name}", view=TimeSelectView('gag', steamid, player_name, str(interaction.user)),
            ephemeral=True
        )
    
    elif action == 'kick':
        await interaction.response.send_modal(KickReasonModal(steamid, player_name, str(interaction.user)))
    
    elif action == 'ban':
        await interaction.response.send_message(
            f"🔨 Ban {player_name}", view=TimeSelectView('ban', steamid, player_name, str(interaction.user)),
            ephemeral=True
        )
    
    elif action == 'slay':
        cmd_id = f"slay_{steamid}_{int(time.time())}"
        
        command = {
            'id': cmd_id,
            'cmd': 'slay',
            'target': steamid,
            'admin': str(interaction.user),
            'timestamp': time.time()
        }
        
        commands_queue.append(command)
        
        await interaction.response.send_message(f"☠ Slay sent!", ephemeral=True)
    
    elif action == 'slap':
        await interaction.response.send_message(
            f"👋 Slap {player_name}", view=DamageSelectView(steamid, player_name, str(interaction.user)),
            ephemeral=True
        )

# ==================== BOT READY ====================

@client.event
async def on_ready():
    print(f'✅ Bot logged in as {client.user}')
    print('🌐 Flask server running at port 27041')

# ==================== MAIN ====================

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    client.run(TOKEN)

import discord
from discord.ext import commands
import os
import asyncio
from flask import Flask
from threading import Thread

# ----------------------
# Configuration
# ----------------------

# Define your role rules here
ROLE_RULES = [
    {
        "requires": ["approved", "male"],
        "grants": "mens"
    },
    {
        "requires": ["approved", "female"],
        "grants": "womens"
    }
]

LOG_CHANNEL_ID = 1388219823384690838  # Replace with your log channel ID

# ----------------------
# Bot Setup
# ----------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------
# Flask App for Uptime
# ----------------------

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask).start()

# ----------------------
# Logging Helper
# ----------------------

async def log_message(message):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)
    else:
        print(f"[LOG] {message}")

# ----------------------
# Role Logic
# ----------------------

async def apply_role_rules(member):
    guild = member.guild
    member_roles = [r.name for r in member.roles]

    for rule in ROLE_RULES:
        required = rule["requires"]
        grant_name = rule["grants"]

        grant_role = discord.utils.get(guild.roles, name=grant_name)
        if not grant_role:
            await log_message(f"❌ Role '{grant_name}' not found.")
            continue

        has_all_required = all(role_name in member_roles for role_name in required)
        has_grant = grant_role in member.roles

        if has_all_required and not has_grant:
            try:
                await member.add_roles(grant_role)
                await log_message(f"✅ Gave **{grant_role.name}** to **{member.display_name}**")
            except Exception as e:
                await log_message(f"❌ Could not add {grant_role.name} to {member.display_name}: {e}")
        elif not has_all_required and has_grant:
            try:
                await member.remove_roles(grant_role)
                await log_message(f"✅ Removed **{grant_role.name}** from **{member.display_name}**")
            except Exception as e:
                await log_message(f"❌ Could not remove {grant_role.name} from {member.display_name}: {e}")

# ----------------------
# Events
# ----------------------

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await log_message(f"🤖 Bot started as {bot.user}")
    await sweep_all_members()

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        await apply_role_rules(after)

# ----------------------
# Commands
# ----------------------

@bot.command()
async def check_roles(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    await apply_role_rules(member)
    await ctx.send(f"🔍 Checked roles for {member.display_name}")

@bot.command()
@commands.has_permissions(administrator=True)
async def sweep_roles(ctx):
    await ctx.send("🔄 Sweeping all members...")
    await log_message(f"🧹 {ctx.author.display_name} triggered a sweep.")
    await sweep_all_members()
    await ctx.send("✅ Sweep complete.")

@bot.command()
@commands.has_permissions(administrator=True)
async def migrate_roles(ctx):
    guild = ctx.guild

    source_role_names = ["T1 men", "T1 women", "ISI men", "ISI women", "4th year cg"]  # Replace with your actual role names
    target_role_name = "YES CG!!"  # Replace with the new role name

    source_roles = [discord.utils.get(guild.roles, name=name) for name in source_role_names]
    target_role = discord.utils.get(guild.roles, name=target_role_name)

    if not target_role or any(r is None for r in source_roles):
        await ctx.send("❌ One or more roles not found. Check role names.")
        return

    updated = 0
    for member in guild.members:
        if any(role in member.roles for role in source_roles):
            try:
                await member.add_roles(target_role)
                for role in source_roles:
                    if role in member.roles:
                        await member.remove_roles(role)
                await log_message(f"🔁 Migrated {member.display_name} → {target_role.name}")
                updated += 1
                await asyncio.sleep(0.1)  # Prevent rate limit issues
            except Exception as e:
                await log_message(f"❌ Failed to migrate {member.display_name}: {e}")

    await ctx.send(f"✅ Migrated {updated} members to {target_role.name}.")
    await log_message(f"✅ Batch role migration completed. {updated} members updated.")



# ----------------------
# Sweep Function (with delay)
# ----------------------

async def sweep_all_members():
    if not bot.guilds:
        await log_message("❌ Bot is not in any servers.")
        return

    guild = bot.guilds[0]
    members = guild.members
    await log_message(f"🔍 Sweeping {len(members)} members...")

    for member in members:
        await apply_role_rules(member)
        await asyncio.sleep(0.1)  # 100ms delay between members

    await log_message("✅ Sweep completed.")

# ----------------------
# Run the Bot
# ----------------------

bot.run(os.environ['BOT_TOKEN'])

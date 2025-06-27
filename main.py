import discord
from discord.ext import commands, tasks
import os
from flask import Flask
from threading import Thread

# ---- Configurable role names ----
ROLE_A = "tester role a"
ROLE_B = "tester role b"
ROLE_C = "give this role"

# ---- Log channel ID (put your channel ID here) ----
LOG_CHANNEL_ID = 605423779715219456  # <-- REPLACE with your actual channel ID (as an int)

# ---- Intents ----
intents = discord.Intents.default()
intents.members = True  # needed to see member roles and receive member update events
intents.message_content = True  # needed for commands

# ---- Bot Setup ----
bot = commands.Bot(command_prefix='!', intents=intents)

# --- Flask app for uptime monitoring ---
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running and alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask).start()

# --- Helper function to send logs to channel ---
async def log_message(message):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)
    else:
        print(f"⚠️ Log channel not found. Message: {message}")

# --- Helper function to sweep all members ---
async def sweep_all_members():
    if not bot.guilds:
        print("❌ Bot is not in any guilds.")
        await log_message("❌ Bot is not in any guilds.")
        return

    guild = bot.guilds[0]  # Adjust if your bot is in multiple servers
    role_a = discord.utils.get(guild.roles, name=ROLE_A)
    role_b = discord.utils.get(guild.roles, name=ROLE_B)
    role_c = discord.utils.get(guild.roles, name=ROLE_C)

    if not all([role_a, role_b, role_c]):
        msg = "❌ One or more roles are missing in the server."
        print(msg)
        await log_message(msg)
        return

    added = 0
    removed = 0

    start_msg = f"🔄 Starting sweep of {len(guild.members)} members..."
    print(start_msg)
    await log_message(start_msg)

    for member in guild.members:
        has_a = role_a in member.roles
        has_b = role_b in member.roles
        has_c = role_c in member.roles

        if has_a and has_b and not has_c:
            try:
                await member.add_roles(role_c)
                added += 1
            except Exception as e:
                err_msg = f"❌ Failed to add {ROLE_C} to {member.display_name}: {e}"
                print(err_msg)
                await log_message(err_msg)
        elif (not has_a or not has_b) and has_c:
            try:
                await member.remove_roles(role_c)
                removed += 1
            except Exception as e:
                err_msg = f"❌ Failed to remove {ROLE_C} from {member.display_name}: {e}"
                print(err_msg)
                await log_message(err_msg)

    done_msg = f"✅ Sweep complete. Added: {added}, Removed: {removed}"
    print(done_msg)
    await log_message(done_msg)

# --- Bot events ---

@bot.event
async def on_ready():
    ready_msg = f'✅ Logged in as {bot.user}'
    print(ready_msg)
    await log_message(ready_msg)
    await sweep_all_members()

@bot.event
async def on_member_update(before, after):
    # Only act if roles changed
    if before.roles == after.roles:
        return

    guild = after.guild
    role_a = discord.utils.get(guild.roles, name=ROLE_A)
    role_b = discord.utils.get(guild.roles, name=ROLE_B)
    role_c = discord.utils.get(guild.roles, name=ROLE_C)

    if not all([role_a, role_b, role_c]):
        msg = "❌ One or more roles are missing from the server."
        print(msg)
        await log_message(msg)
        return

    has_a = role_a in after.roles
    has_b = role_b in after.roles
    has_c = role_c in after.roles

    # Add Role C if conditions met
    if has_a and has_b and not has_c:
        try:
            await after.add_roles(role_c)
            msg = f"✅ Added {ROLE_C} to {after.display_name}"
            print(msg)
            await log_message(msg)
        except Exception as e:
            err_msg = f"❌ Failed to add {ROLE_C} to {after.display_name}: {e}"
            print(err_msg)
            await log_message(err_msg)

    # Remove Role C if conditions not met
    elif (not has_a or not has_b) and has_c:
        try:
            await after.remove_roles(role_c)
            msg = f"✅ Removed {ROLE_C} from {after.display_name}"
            print(msg)
            await log_message(msg)
        except Exception as e:
            err_msg = f"❌ Failed to remove {ROLE_C} from {after.display_name}: {e}"
            print(err_msg)
            await log_message(err_msg)

# --- Commands ---

@bot.command(name='check_roles')
async def check_roles(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    role_a = discord.utils.get(ctx.guild.roles, name=ROLE_A)
    role_b = discord.utils.get(ctx.guild.roles, name=ROLE_B)
    role_c = discord.utils.get(ctx.guild.roles, name=ROLE_C)

    if not all([role_a, role_b, role_c]):
        await ctx.send("❌ One or more roles are missing in the server.")
        return

    has_a = role_a in member.roles
    has_b = role_b in member.roles
    has_c = role_c in member.roles

    if has_a and has_b and not has_c:
        try:
            await member.add_roles(role_c)
            await ctx.send(f"✅ {member.mention} has been given **{ROLE_C}**.")
            await log_message(f"✅ {member.display_name} given {ROLE_C} by command !check_roles")
        except Exception as e:
            await ctx.send(f"❌ Failed to add role: {e}")
    elif has_c:
        await ctx.send(f"ℹ️ {member.mention} already has **{ROLE_C}**.")
    else:
        await ctx.send(f"❌ {member.mention} does not meet the role requirements.")

@bot.command(name='sweep_roles')
@commands.has_permissions(administrator=True)  # Optional: admin-only
async def sweep_roles(ctx):
    await ctx.send("🔄 Starting sweep for all members...")
    await log_message(f"🔄 {ctx.author.display_name} triggered sweep_roles command.")
    await sweep_all_members()
    await ctx.send("✅ Sweep complete.")

# --- Run bot ---
bot.run(os.environ['BOT_TOKEN'])

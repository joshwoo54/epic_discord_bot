import discord
from discord.ext import commands, tasks
import os
from flask import Flask
from threading import Thread

# ---- Configurable role names ----
ROLE_A = "Role A"
ROLE_B = "Role B"
ROLE_C = "Role C"

# ---- Intents ----
intents = discord.Intents.default()
intents.members = True  # needed to see member roles and receive member update events
intents.message_content = True  # needed if you want to use commands

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

# --- Helper function to sweep all members ---
async def sweep_all_members():
    if not bot.guilds:
        print("❌ Bot is not in any guilds.")
        return

    guild = bot.guilds[0]  # If your bot is in multiple servers, adjust accordingly
    role_a = discord.utils.get(guild.roles, name=ROLE_A)
    role_b = discord.utils.get(guild.roles, name=ROLE_B)
    role_c = discord.utils.get(guild.roles, name=ROLE_C)

    if not all([role_a, role_b, role_c]):
        print("❌ One or more roles are missing in the server.")
        return

    added = 0
    removed = 0

    print(f"🔄 Starting sweep of {len(guild.members)} members...")

    for member in guild.members:
        has_a = role_a in member.roles
        has_b = role_b in member.roles
        has_c = role_c in member.roles

        if has_a and has_b and not has_c:
            try:
                await member.add_roles(role_c)
                added += 1
            except Exception as e:
                print(f"❌ Failed to add {ROLE_C} to {member.display_name}: {e}")
        elif (not has_a or not has_b) and has_c:
            try:
                await member.remove_roles(role_c)
                removed += 1
            except Exception as e:
                print(f"❌ Failed to remove {ROLE_C} from {member.display_name}: {e}")

    print(f"✅ Sweep complete. Added: {added}, Removed: {removed}")

# --- Bot events ---

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    await sweep_all_members()

@bot.event
async def on_member_update(before, after):
    # Check roles only if roles changed
    if before.roles == after.roles:
        return

    guild = after.guild
    role_a = discord.utils.get(guild.roles, name=ROLE_A)
    role_b = discord.utils.get(guild.roles, name=ROLE_B)
    role_c = discord.utils.get(guild.roles, name=ROLE_C)

    if not all([role_a, role_b, role_c]):
        print("❌ One or more roles are missing from the server.")
        return

    has_a = role_a in after.roles
    has_b = role_b in after.roles
    has_c = role_c in after.roles

    # Add Role C if has A and B and missing C
    if has_a and has_b and not has_c:
        try:
            await after.add_roles(role_c)
            print(f"✅ Added {ROLE_C} to {after.display_name}")
        except Exception as e:
            print(f"❌ Failed to add {ROLE_C}: {e}")

    # Remove Role C if missing A or B but has C
    elif (not has_a or not has_b) and has_c:
        try:
            await after.remove_roles(role_c)
            print(f"✅ Removed {ROLE_C} from {after.display_name}")
        except Exception as e:
            print(f"❌ Failed to remove {ROLE_C}: {e}")

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
        except Exception as e:
            await ctx.send(f"❌ Failed to add role: {e}")
    elif has_c:
        await ctx.send(f"ℹ️ {member.mention} already has **{ROLE_C}**.")
    else:
        await ctx.send(f"❌ {member.mention} does not meet the role requirements.")

@bot.command(name='sweep_roles')
@commands.has_permissions(administrator=True)  # Optional: restrict to admins
async def sweep_roles(ctx):
    await ctx.send("🔄 Starting sweep for all members...")
    await sweep_all_members()
    await ctx.send("✅ Sweep complete.")

# --- Run bot ---
bot.run(os.environ['BOT_TOKEN'])

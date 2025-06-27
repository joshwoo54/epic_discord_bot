import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# ------------ Bot Setup ------------ #

intents = discord.Intents.default()
intents.members = True  # Needed to read member roles
bot = commands.Bot(command_prefix='!', intents=intents)

# Customize role names
ROLE_A = "Role A"
ROLE_B = "Role B"
ROLE_C = "Role C"

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')

@bot.event
async def on_member_update(before, after):
    guild = after.guild
    role_a = discord.utils.get(guild.roles, name=ROLE_A)
    role_b = discord.utils.get(guild.roles, name=ROLE_B)
    role_c = discord.utils.get(guild.roles, name=ROLE_C)

    if not all([role_a, role_b, role_c]):
        print("❌ One or more roles are missing.")
        return

    has_a = role_a in after.roles
    has_b = role_b in after.roles
    has_c = role_c in after.roles

    print(f"🔄 Role update for {after.name}: A={has_a}, B={has_b}, C={has_c}")

    # Add Role C if both A and B are present
    if has_a and has_b and not has_c:
        try:
            await after.add_roles(role_c)
            print(f"✅ Added {role_c.name} to {after.display_name}")
        except Exception as e:
            print(f"❌ Failed to add role: {e}")

    # Remove Role C if either A or B is missing
    elif (not has_a or not has_b) and has_c:
        try:
            await after.remove_roles(role_c)
            print(f"🗑️ Removed {role_c.name} from {after.display_name}")
        except Exception as e:
            print(f"❌ Failed to remove role: {e}")

# ------------ Commands ------------ #

@bot.command()
async def check_roles(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    role_a = discord.utils.get(ctx.guild.roles, name=ROLE_A)
    role_b = discord.utils.get(ctx.guild.roles, name=ROLE_B)
    role_c = discord.utils.get(ctx.guild.roles, name=ROLE_C)

    if not all([role_a, role_b, role_c]):
        await ctx.send("❌ One or more roles are missing.")
        return

    has_a = role_a in member.roles
    has_b = role_b in member.roles
    has_c = role_c in member.roles

    if has_a and has_b:
        if not has_c:
            await member.add_roles(role_c)
            await ctx.send(f'✅ {member.mention} has been given **{role_c.name}**.')
        else:
            await ctx.send(f'ℹ️ {member.mention} already has **{role_c.name}**.')
    else:
        if has_c:
            await member.remove_roles(role_c)
            await ctx.send(f'🗑️ {member.mention} lost **{role_c.name}** (missing A or B).')
        else:
            await ctx.send(f'❌ {member.mention} does not meet the role requirements.')

@bot.command()
@commands.has_permissions(administrator=True)
async def sweep_roles(ctx):
    """Check all members and assign/remove Role C as needed."""
    role_a = discord.utils.get(ctx.guild.roles, name=ROLE_A)
    role_b = discord.utils.get(ctx.guild.roles, name=ROLE_B)
    role_c = discord.utils.get(ctx.guild.roles, name=ROLE_C)

    if not all([role_a, role_b, role_c]):
        await ctx.send("❌ One or more roles are missing.")
        return

    added, removed = 0, 0

    for member in ctx.guild.members:
        has_a = role_a in member.roles
        has_b = role_b in member.roles
        has_c = role_c in member.roles

        if has_a and has_b and not has_c:
            try:
                await member.add_roles(role_c)
                added += 1
            except:
                pass
        elif (not has_a or not has_b) and has_c:
            try:
                await member.remove_roles(role_c)
                removed += 1
            except:
                pass

    await ctx.send(f"✅ Sweep done. Added: {added}, Removed: {removed}")

# ------------ Flask Web Server (UptimeRobot) ------------ #

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running and alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# ------------ Run the Bot ------------ #

bot.run(os.environ['BOT_TOKEN'])

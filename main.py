import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# Intents setup
intents = discord.Intents.default()
intents.members = True  # Needed for role checking

# Bot setup
bot = commands.Bot(command_prefix='!', intents=intents)

# Role names (customize these to match your server)
ROLE_A = "tester role a"
ROLE_B = "tester role b"
ROLE_C = "give this role"

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')

# Event: Member's roles updated
@bot.event
async def on_member_update(before, after):
    print(f"🔄 Detected role update for {after.name}")
    guild = after.guild
    role_a = discord.utils.get(guild.roles, name=ROLE_A)
    role_b = discord.utils.get(guild.roles, name=ROLE_B)
    role_c = discord.utils.get(guild.roles, name=ROLE_C)

    print(f"🔍 Checking roles for {after.name}")
    print(f"Role A: {role_a in after.roles}")
    print(f"Role B: {role_b in after.roles}")
    print(f"Already has Role C: {role_c in after.roles}")

    if not all([role_a, role_b, role_c]):
        print("❌ One or more roles are missing from the server.")
        return

    if role_a in after.roles and role_b in after.roles and role_c not in after.roles:
        try:
            await after.add_roles(role_c)
            print(f"✅ Gave {role_c.name} to {after.display_name}")
        except Exception as e:
            print(f"❌ Failed to assign role: {e}")

# Optional: Manual command to check a member
@bot.command()
async def check_roles(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    role_a = discord.utils.get(ctx.guild.roles, name=ROLE_A)
    role_b = discord.utils.get(ctx.guild.roles, name=ROLE_B)
    role_c = discord.utils.get(ctx.guild.roles, name=ROLE_C)

    if role_a in member.roles and role_b in member.roles:
        if role_c not in member.roles:
            await member.add_roles(role_c)
            await ctx.send(f'{member.mention} has been given **{role_c.name}**.')
        else:
            await ctx.send(f'{member.mention} already has **{role_c.name}**.')
    else:
        await ctx.send(f'{member.mention} does not meet the role requirements.')

# ----------------------------
# Flask web server (for UptimeRobot)
# ----------------------------

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running and alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# Start the bot with your token from Secrets
bot.run(os.environ['BOT_TOKEN'])

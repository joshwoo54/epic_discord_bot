import discord
from discord.ext import commands
import os
import asyncio
from flask import Flask
from flask import Response
from threading import Thread
from collections import defaultdict
from datetime import datetime, time
import pytz
from dateutil import parser
import time as pytime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from media_sheet import setup_media_sheet_task
from event_sheet import setup_event_sheet_task

# ----------------------
# Configuration
# ----------------------

# Define your role rules here
MERGED_ROLE_RULES = [
    # Approval for mens/womens channels
    {"grants": "mens", "any_requires": [["approved", "male"]]},
    {"grants": "womens", "any_requires": [["approved", "female"]]},

    # Class approvals
    {"grants": "1st year approved", "any_requires": [["approved", "1st year"]]},
    {"grants": "2nd year approved", "any_requires": [["approved", "2nd year"]]},
    {"grants": "3rd year approved", "any_requires": [["approved", "3rd year"]]},
    {"grants": "4th year approved", "any_requires": [["approved", "4th year"]]},
    {"grants": "5th+ year approved", "any_requires": [["approved", "5th+ year"]]},
    {"grants": "alumni approved", "any_requires": [["approved", "alumni"]]},

    # CG roles with OR conditions
    {"grants": "T1 men", "any_requires": [["1st year approved", "male", "YES CG!!"]]},
    {"grants": "T1 women", "any_requires": [["1st year approved", "female", "YES CG!!"]]},

    {
        "grants": "ISI men",
        "any_requires": [
            ["2nd year approved", "male", "YES CG!!"],
            ["3rd year approved", "male", "YES CG!!"]
        ]
    },
    {
        "grants": "ISI women",
        "any_requires": [
            ["2nd year approved", "female", "YES CG!!"],
            ["3rd year approved", "female", "YES CG!!"]
        ]
    },
    {
        "grants": "4th year cg",
        "any_requires": [
            ["4th year approved", "YES CG!!"],
            ["5th+ year approved", "YES CG!!"]
        ]
    },
]


LOG_CHANNEL_ID = 1388219823384690838  # Replace with your log channel ID
UPDATE_COOLDOWN = 3  # seconds
recent_updates = defaultdict(float)
sweeping = False

# ----------------------
# Bot Setup
# ----------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# for web service
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
# Flask App for google sites links
# ----------------------

@app.route("/media-links")
def media_links():
    from media_sheet import spreadsheet, SHEET_TABS
    now = datetime.now(pytz.timezone("America/Los_Angeles"))
    logger.info("🌐 Media-links called, now = %s", now)

    html = """
    <html>
    <head>
      <title>Active Media Links</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
                       Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
          background: #f9f9f9;
          color: #333;
          padding: 20px;
          max-width: 600px;
          margin: auto;
        }
        h1 {
          text-align: center;
          color: #2c3e50;
        }
        ul {
          list-style-type: none;
          padding: 0;
        }
        li {
          background: #fff;
          margin: 8px 0;
          padding: 12px 16px;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: background-color 0.3s ease;
        }
        li:hover {
          background-color: #e1f0ff;
        }
        a {
          color: #2980b9;
          text-decoration: none;
          font-weight: 600;
        }
        a:hover {
          text-decoration: underline;
        }
        .tab-header {
          margin-top: 40px;
          margin-bottom: 10px;
          font-size: 1.25rem;
          color: #34495e;
          border-bottom: 2px solid #2980b9;
          padding-bottom: 4px;
        }
        .no-links {
          font-style: italic;
          color: #888;
          margin: 10px 0 20px 0;
        }
      </style>
    </head>
    <body>
      <h1>Active Media Links</h1>
    """

    for tab_name in SHEET_TABS:
        logger.info(f"➡️ Loading tab '{tab_name}'")
        try:
            ws = spreadsheet.worksheet(tab_name)
            rows = ws.get_all_values()
            logger.info(f"   ✅ Loaded {len(rows)} rows")
        except Exception as e:
            logger.error(f"   ❌ Failed to load tab {tab_name}: {e}")
            continue

        active_links = []

        for i, row in enumerate(rows):
            if i < 2:
                continue  # Skip header rows

            row += [""] * 11  # Pad row to avoid index errors

            link = row[8].strip()  # Link URL (col I)
            start_str = row[9].strip()  # Start date (col J)
            end_str = row[10].strip()  # End date (col K)
            link_name = row[3].strip()  # Link text/name (col D)

            logger.info(f"   Row {i+1}: link='{link}', start='{start_str}', end='{end_str}', name='{link_name}'")

            if not link or not start_str or not end_str:
                continue

            try:
                tz = pytz.timezone("America/Los_Angeles")
                start_date = parser.parse(start_str).date()
                end_date = parser.parse(end_str).date()
                start = tz.localize(datetime.combine(start_date, time.min))
                end = tz.localize(datetime.combine(end_date, time.max))
                logger.info(f"     Parsed window: {start} → {end}")
            except Exception as e:
                logger.error(f"     ❌ Date parse error (row {i+1}): {e}")
                continue

            if start <= now <= end:
                active_links.append((link_name or link, link))

        if active_links:
            html += f'<div class="tab-header">{tab_name}</div><ul>'
            for name, url in active_links:
                safe_name = name if name else url
                html += f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{safe_name}</a></li>'
            html += '</ul>'
        else:
            html += f'<div class="tab-header">{tab_name}</div>'
            html += '<p class="no-links">No active links at this time.</p>'

    html += "</body></html>"

    return Response(html, mimetype="text/html")



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
    changed = False

    for rule in MERGED_ROLE_RULES:
        grant_name = rule["grants"]
        grant_role = discord.utils.get(guild.roles, name=grant_name)
        if not grant_role:
            await log_message(f"❌ Role '{grant_name}' not found.")
            continue

        eligible = any(all(role in member_roles for role in group) for group in rule["any_requires"])
        has_grant = grant_role in member.roles

        if eligible and not has_grant:
            try:
                await member.add_roles(grant_role)
                await log_message(f"➕ Gave **{grant_role.name}** to **{member.display_name}**")
                changed = True
            except Exception as e:
                await log_message(f"❌ Could not add {grant_role.name} to {member.display_name}: {e}")
        elif not eligible and has_grant:
            try:
                await member.remove_roles(grant_role)
                await log_message(f"➖ Removed **{grant_role.name}** from **{member.display_name}**")
                changed = True
            except Exception as e:
                await log_message(f"❌ Could not remove {grant_role.name} from {member.display_name}: {e}")

    return changed



# ----------------------
# Events
# ----------------------

media_sheet_task_started = False
event_sheet_task_started = False

@bot.event
async def on_ready():
    global media_sheet_task_started
    global event_sheet_task_started
    print(f"✅ Logged in as {bot.user}")
    await log_message(f"🤖 Bot started as {bot.user}")
    await sweep_all_members()

    if not media_sheet_task_started:
        setup_media_sheet_task(bot)
        media_sheet_task_started = True
    
    if not event_sheet_task_started:
        setup_event_sheet_task(bot)
        event_sheet_task_started = True


# @bot.event
# async def on_ready():
#     print(f"✅ Logged in as {bot.user}")
#     await log_message(f"🤖 Bot started as {bot.user}")
#     await sweep_all_members()

@bot.event
async def on_member_update(before, after):
    global sweeping
    if sweeping:
        return

    if set(before.roles) == set(after.roles):
        return  # No role change

    now = time.time()
    if now - recent_updates[after.id] < UPDATE_COOLDOWN:
        return
    recent_updates[after.id] = now

    await asyncio.sleep(1.5)  # Let Discord finish processing roles
    await apply_role_rules(after)

# ----------------------
# Commands
# ----------------------

@bot.command()
async def check_roles(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    await ctx.send(f"🔍 Checking roles for {member.display_name}")
    await apply_role_rules(member)
    await ctx.send(f"✅ Check complete.")

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

    source_role_names = ["4th year", "5th+ year"]
    target_role_name = "alumni"

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
                await asyncio.sleep(0.1)
            except Exception as e:
                await log_message(f"❌ Failed to migrate {member.display_name}: {e}")

    await ctx.send(f"✅ Migrated {updated} members to {target_role.name}.")
    await log_message(f"✅ Batch role migration completed. {updated} members updated.")

# ----------------------
# Sweep Function (with delay)
# ----------------------

async def sweep_all_members():
    global sweeping
    sweeping = True
    changed_count = 0

    try:
        if not bot.guilds:
            await log_message("❌ Bot is not in any servers.")
            return

        guild = bot.guilds[0]
        members = guild.members
        await log_message(f"🔍 Sweeping {len(members)} members...")

        for member in members:
            changed = await apply_role_rules(member)
            if changed:
                changed_count += 1
            await asyncio.sleep(0.5)  # delay to prevent rate limits

    finally:
        sweeping = False
        await log_message(f"✅ Sweep completed. {changed_count} members had roles changed.")


# ----------------------
# Run the Bot
# ----------------------

bot.run(os.environ['BOT_TOKEN'])

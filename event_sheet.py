import os, json, asyncio
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from discord.ext import tasks
from datetime import datetime

SERVICE_ACCOUNT_INFO = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar"
]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
gc = gspread.authorize(creds)
calendar_service = build("calendar", "v3", credentials=creds)

SECOND_SHEET_URL = "https://docs.google.com/spreadsheets/d/1wQbS8JCmKjNx7M43EuDW9HBfnOY25VkjnnYxBc70y0g/edit?usp=sharing"
SECOND_SHEET_TABS = ["Form Responses 1"]

CHANNEL_Z_ID = 1395968665287135262  #etl
STATUS_COL_AA = 27
STATUS_COL_AB = 28

CHANNEL_MAP = {
    "large group": 1388258914629451917,
    "outreach": 1388259127528259645,
    "inreach": 1388259483335135232,
    "media": 1388259539714969830,
    "mens isi": 1388259626906030252,
    "womens isi": 1388259678391242864,
    "4th year cg": 1388259730958450889,
    "worship": 1388259786990030928,
    "boyts T1": 1388259868959441047,
    "girls T1": 1388259923078549504,
    "retreats": 1388259981001887744,
}

spreadsheet = gc.open_by_url(SECOND_SHEET_URL)

def create_calendar_event(summary, start_dt, end_dt, calendar_id="epicsanluisobispo@gmail.com"):
    event = {
        "summary": summary,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "America/Los_Angeles"},
    }
    result = calendar_service.events().insert(calendarId=calendar_id, body=event).execute()
    return result.get("htmlLink")

def parse_datetime(date_str, time_str):
    formats = ("%m/%d/%Y %I:%M:%S %p", "%Y-%m-%d %I:%M:%S %p")
    for fmt in formats:
        try:
            return datetime.strptime(f"{date_str} {time_str}", fmt)
        except ValueError:
            continue
    return None

def setup_event_sheet_task(bot):
    @tasks.loop(seconds=60)
    async def check_second_sheet():
        for tab_name in SECOND_SHEET_TABS:
            try:
                sheet = await asyncio.to_thread(spreadsheet.worksheet, tab_name)
                all_rows = await asyncio.to_thread(sheet.get_all_values)
            except Exception as e:
                print(f"[Error in '{tab_name}']: {e}")
                continue

            for i, row in enumerate(all_rows):
                if i < 1:
                    continue

                row += [""] * max(0, STATUS_COL_AB - len(row))
                b = row[1].strip()               # Column B (Name)
                c = row[2].strip().lower()       # Column C (Ministry Team)
                g = row[6].strip()               # Column G (Event Name, recurring)
                l = row[11].strip()              # Column L (Event Name, one time)
                m = row[12].strip()              # Column M (Date, one time)
                n = row[13].strip()              # Column N (start time, one time)
                o = row[14].strip()              # Column O (end time, one time)
                x = row[23].strip().lower()      # Column X (Josh approve)
                y = row[24].strip().lower()      # Column Y (Nikki approve)
                z = row[25].strip().lower()      # Column Z (Ellie approve)
                status_aa = row[STATUS_COL_AA - 1].strip().lower()
                status_ab = row[STATUS_COL_AB - 1].strip().lower()

                if b and status_aa != "sent":
                    chan = bot.get_channel(CHANNEL_Z_ID)
                    if chan:
                        await chan.send(f"📌 **{b}** has filled out the **event request form** on behalf of **{c}** team. Please review!")
                        await asyncio.to_thread(sheet.update_cell, i+1, STATUS_COL_AA, "SENT")

                if x == y == z == "approved" and status_ab != "sent":
                    description = g or l or "a request"
                    if c in CHANNEL_MAP:
                        chan = bot.get_channel(CHANNEL_MAP[c])
                        if chan:
                            await chan.send(f"✅ Your event request for **{description}** has been approved by the ETLs!")
                            await asyncio.to_thread(sheet.update_cell, i+1, STATUS_COL_AB, "SENT")

                            if m and n and o:
                                start_dt = parse_datetime(m, n)
                                end_dt = parse_datetime(m, o)
                                if start_dt and end_dt:
                                    try:
                                        await asyncio.to_thread(create_calendar_event, description, start_dt, end_dt)
                                        cal_chan = bot.get_channel(CHANNEL_Z_ID)
                                        if cal_chan:
                                            await cal_chan.send(f"📅 **{l}** successfully added to the Epic Calendar!")
                                    except Exception as ce:
                                        print(f"🛑 Calendar event failed: {ce}")
                    else:
                        print(f"⚠️ Unknown category '{c}' in row {i+1}")
    check_second_sheet.start()

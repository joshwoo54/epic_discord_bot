import os
import json
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from discord.ext import tasks
from datetime import datetime

# --------------------
# Google API Setup
# --------------------
SERVICE_ACCOUNT_INFO = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar"
]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
gc = gspread.authorize(creds)
calendar_service = build("calendar", "v3", credentials=creds)

# --------------------
# Sheet Configuration
# --------------------
SECOND_SHEET_URL = "https://docs.google.com/spreadsheets/d/1wQbS8JCmKjNx7M43EuDW9HBfnOY25VkjnnYxBc70y0g/edit?usp=sharing"
SECOND_SHEET_TABS = ["Form Responses 1"]  # Add more if needed

CHANNEL_Z_ID = 1395968665287135262  # Alert etl when event request submitted

STATUS_COL_AA = 27  # Column AA — for etl sent status
STATUS_COL_AB = 28  # Column AB — for team sent status

# Map categories from column C to Discord channel IDs
CHANNEL_MAP = {
    "large group": 999999999999999999,
    "outreach": 999999999999999999,
    "inreach": 999999999999999999,
    "media": 1396014983602769972,
    "mens isi": 999999999999999999,
    "womens isi": 999999999999999999,
    "4th year cg": 999999999999999999,
    "worship": 999999999999999999,
    "boyts T1": 999999999999999999,
    "girls T1": 999999999999999999,
    "retreats": 999999999999999999,
}

spreadsheet = gc.open_by_url(SECOND_SHEET_URL)

# --------------------
# Calendar Event Creator
# --------------------
def create_calendar_event(summary, start_dt, end_dt, calendar_id="epicsanluisobispo@gmail.com"):
    event = {
        "summary": summary,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "America/Los_Angeles",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "America/Los_Angeles",
        },
    }

    event_result = calendar_service.events().insert(calendarId=calendar_id, body=event).execute()
    return event_result.get("htmlLink")


# --------------------
# Date & Time Formatter
# --------------------
def parse_datetime(date_str, time_str):
    try:
        # Try format like "7/31/2025 5:30:00 AM"
        return datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %I:%M:%S %p")
    except ValueError:
        try:
            # Try ISO-like format: "2025-07-31 5:30:00 AM"
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M:%S %p")
        except ValueError:
            return None


# --------------------
# Sheet Task Setup
# --------------------
def setup_event_sheet_task(bot):
    @tasks.loop(seconds=60)
    async def check_second_sheet():
        try:
            for tab_name in SECOND_SHEET_TABS:
                try:
                    sheet = spreadsheet.worksheet(tab_name)
                    all_rows = sheet.get_all_values()

                    for i, row in enumerate(all_rows):
                        if i < 1:
                            continue  # Skip headers

                        while len(row) < STATUS_COL_AB:
                            row.append("")

                        b_val = row[1].strip()               # Column B (Name)
                        c_val = row[2].strip().lower()       # Column C (Ministry Team)
                        g_val = row[6].strip()               # Column G (Event Name, recurring)
                        l_val = row[11].strip()              # Column L (Event Name, one time)
                        m_val = row[12].strip()              # Column M (Date, one time)
                        n_val = row[13].strip()              # Column N (start time, one time)
                        o_val = row[14].strip()              # Column O (end time, one time)
                        x_val = row[23].strip().lower()      # Column X (Josh approve)
                        y_val = row[24].strip().lower()      # Column Y (Nikki approve)
                        z_val = row[25].strip().lower()      # Column Z (Ellie approve)

                        status_aa = row[STATUS_COL_AA - 1].strip().lower()
                        status_ab = row[STATUS_COL_AB - 1].strip().lower()

                        # ---- Condition 1: form filled alert etl
                        if b_val and status_aa != "sent":
                            channel = bot.get_channel(CHANNEL_Z_ID)
                            if channel:
                                msg = f"📌 **{b_val}** has filled out the **event request form** on behalf of **{c_val}** team. Please review!"
                                await channel.send(msg)
                                sheet.update_cell(i + 1, STATUS_COL_AA, "SENT")

                        # ---- Condition 2: event approved send to team
                        if x_val == "approved" and y_val == "approved" and z_val == "approved" and status_ab != "sent":
                            request_description = g_val if g_val else l_val if l_val else "a request"
                            if c_val in CHANNEL_MAP:
                                channel = bot.get_channel(CHANNEL_MAP[c_val])
                                if channel:
                                    msg = f"✅ Your event request for **{request_description}** has been approved by the ETLs!"
                                    await channel.send(msg)
                                    sheet.update_cell(i + 1, STATUS_COL_AB, "SENT")

                                    # Calendar integration if M/N/O provided
                                    if m_val and n_val and o_val:
                                        start_dt = parse_datetime(m_val, n_val)
                                        end_dt = parse_datetime(m_val, o_val)
                                        if start_dt and end_dt:
                                            try:
                                                create_calendar_event(request_description, start_dt, end_dt)
                                                print(f"📅 Event added for '{request_description}' on {m_val}")
                                                calendar_channel = bot.get_channel(CHANNEL_Z_ID)
                                                if calendar_channel:
                                                    msg = f"📅 **{l_val}** sucessfully added to the Epic Calendar!"
                                                    await channel.send(msg)
                                            except Exception as cal_err:
                                                print(f"🛑 Calendar event failed: {cal_err}")
                            else:
                                print(f"⚠️ Unknown category '{c_val}' in row {i+1}")

                except Exception as tab_err:
                    print(f"[Second Sheet Error in '{tab_name}']: {tab_err}")

        except Exception as e:
            print(f"[Second SheetBot Error] {e}")

    check_second_sheet.start()

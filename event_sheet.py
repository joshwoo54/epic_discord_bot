import os
import json
import gspread
from google.oauth2.service_account import Credentials
from discord.ext import tasks

# --------------------
# Google Sheets Setup
# --------------------
SERVICE_ACCOUNT_INFO = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
gc = gspread.authorize(creds)

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
                        if i < 2:
                            continue  # Skip headers

                        while len(row) < STATUS_COL_AB:
                            row.append("")

                        b_val = row[1].strip()               # Column B
                        c_val = row[2].strip().lower()       # Column C (category)
                        g_val = row[6].strip()               # Column G
                        l_val = row[11].strip()              # Column L
                        x_val = row[23].strip().lower()      # Column X
                        y_val = row[24].strip().lower()      # Column Y
                        z_val = row[25].strip().lower()      # Column Z

                        status_aa = row[STATUS_COL_AA - 1].strip().lower()
                        status_ab = row[STATUS_COL_AB - 1].strip().lower()

                        # ---- Condition 1: form filled alert etl
                        if b_val and status_aa != "sent":
                            channel = bot.get_channel(CHANNEL_Z_ID)
                            if channel:
                                msg = f"📌 **{b_val}** has filled out the **event request form** on behalf of **{c_val}**. Please review!"
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
                            else:
                                print(f"⚠️ Unknown category '{c_val}' in row {i+1}")

                except Exception as tab_err:
                    print(f"[Second Sheet Error in '{tab_name}']: {tab_err}")

        except Exception as e:
            print(f"[Second SheetBot Error] {e}")

    check_second_sheet.start()

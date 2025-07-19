import gspread
from discord.ext import tasks

SHEET_URL = "https://docs.google.com/spreadsheets/d/15pvTgbZSvFKl5PHBDC-WRhRYE3tF_XWu8qkoCRivCtM/edit?usp=sharing"
SHEET_TABS = ["Fall Quarter", "Winter Quarter", "Spring Quarter"]

CHANNEL_Z_ID = 1395968665287135262  # to alert etls (if name filled out)
CHANNEL_X_ID = 1396014983602769972  # to alert media team (if etl approved and either instagram post/story)
CHANNEL_Y_ID = 1396015081770455121    # to alert lg slides team (if etl approved and lg slide)

STATUS_COL_V = 22  # Column V for condition 1 (mark as send to etl)
STATUS_COL_W = 23  # Column W for conditions 2 & 3 (mark as send to lg/media team)

gc = gspread.public()
spreadsheet = gc.open_by_url(SHEET_URL)

def setup_sheet_task(bot):
    @tasks.loop(seconds=60)
    async def check_sheet():
        try:
            for tab_name in SHEET_TABS:
                try:
                    sheet = spreadsheet.worksheet(tab_name)
                    all_rows = sheet.get_all_values()

                    for i, row in enumerate(all_rows):
                        if i < 1:
                            continue  # skip header

                        # Ensure row has enough columns to avoid index errors
                        while len(row) < STATUS_COL_W:
                            row.append('')

                        a_val = row[0].strip().lower()   # Column A, etl approved
                        b_val = row[1].strip()           # Column B, requester name
                        d_val = row[3].strip()           # Column D, event name
                        j_val = row[9].strip().lower()   # Column J, instagram post
                        k_val = row[10].strip().lower()  # Column K, instagram story
                        p_val = row[15].strip().lower()  # Column P, lg slide

                        status_v = row[STATUS_COL_V - 1].strip().lower()  # Column V, mark etl
                        status_w = row[STATUS_COL_W - 1].strip().lower()  # Column W, mark lg/slide team

                        # Condition 1: send to etl
                        if b_val and status_v != "sent":
                            channel = bot.get_channel(CHANNEL_Z_ID)
                            if channel:
                                msg = f"📢 **{b_val}** has added {d_val} to the media live sheet. Waiting to be reviewed!"
                                await channel.send(msg)
                                sheet.update_cell(i + 1, STATUS_COL_V, "SENT")
                            continue  # skip checking other conditions for this row

                        # Condition 2 and 3 require A == "yes" and sent NOT marked in W
                        if a_val == "yes" and status_w != "sent":

                            sent_flag = False

                            # Condition 2: send to media team
                            if j_val == "true" or k_val == "true":
                                channel = bot.get_channel(CHANNEL_X_ID)
                                if channel:
                                    msg = f"📢 The ETL's have approved **{b_val}**'s media request of {d_val}. They are requesting an Instagram post/story. Please check the media live sheet!"
                                    await channel.send(msg)
                                    sent_flag = True

                            # Condition 3: send to lg slides team
                            if p_val == "true":
                                channel = bot.get_channel(CHANNEL_Y_ID)
                                if channel:
                                    msg = f"📢 The ETL's have approved **{b_val}**'s media request of {d_val}. They are requesting a large group slide. Please check the media live sheet!"
                                    await channel.send(msg)
                                    sent_flag = True

                            if sent_flag:
                                sheet.update_cell(i + 1, STATUS_COL_W, "SENT")

                except Exception as tab_err:
                    print(f"[Error in sheet '{tab_name}']: {tab_err}")

        except Exception as e:
            print(f"[SheetBot Error] {e}")

    check_sheet.start()

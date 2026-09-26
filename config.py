import os

from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME")
ACCOUNTS_WORKSHEET_NAME = os.getenv("ACCOUNTS_WORKSHEET_NAME", "Accounts")
ACCOUNT_MOVEMENTS_WORKSHEET_NAME = os.getenv(
    "ACCOUNT_MOVEMENTS_WORKSHEET_NAME",
    "Account Movements",
)
GOALS_WORKSHEET_NAME = os.getenv("GOALS_WORKSHEET_NAME", "Goals")
SETTINGS_WORKSHEET_NAME = os.getenv("SETTINGS_WORKSHEET_NAME", "Settings")

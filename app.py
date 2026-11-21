import streamlit as st
import json
import os
import hashlib
import copy
import html
import hmac
import secrets
import re
import time
import sqlite3
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo, available_timezones

# =========================================================
# TIMEZONE — USER SELECTABLE
# =========================================================
# Family timezone is selected during parent setup and stored in settings.
# Older accounts default to Asia/Kolkata (India Standard Time).
DEFAULT_TIMEZONE = "Asia/Kolkata"
AVAILABLE_TIMEZONES = sorted(available_timezones())

def get_selected_timezone():
    """Return the family's selected ZoneInfo timezone safely."""
    current_data = st.session_state.get("data", {})
    current_settings = current_data.get("settings", {}) if isinstance(current_data, dict) else {}
    timezone_name = current_settings.get("timezone", DEFAULT_TIMEZONE)
    try:
        return ZoneInfo(timezone_name)
    except (KeyError, ValueError):
        return ZoneInfo(DEFAULT_TIMEZONE)

def now_local():
    """Return the current datetime in the family's selected timezone."""
    return datetime.now(get_selected_timezone())



# =========================================================
# ONE-TIME ONBOARDING REPLAY FOR TESTING
# =========================================================
# Increase this number in a future test build if you want to replay
# the first-time experience again without deleting family data.
ONBOARDING_REPLAY_VERSION = 2

# =========================================================
# APP SETTINGS
# =========================================================

st.set_page_config(
    page_title="Good Deeds",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = "good_deeds_data.json"  # legacy single-family file, used for migration only
ACCOUNTS_DB_FILE = "good_deeds_accounts.db"
OTP_VALID_SECONDS = 300  # 5 minutes

# =========================================================
# COUNTRY CODES
# =========================================================

COUNTRY_CODES = {
    "🇮🇳 India (+91)": "+91",
    "🇺🇸 United States / Canada (+1)": "+1",
    "🇬🇧 United Kingdom (+44)": "+44",
    "🇦🇺 Australia (+61)": "+61",
    "🇦🇪 UAE (+971)": "+971",
    "🇸🇬 Singapore (+65)": "+65",
    "🇳🇿 New Zealand (+64)": "+64",
    "🇿🇦 South Africa (+27)": "+27",
    "🇩🇪 Germany (+49)": "+49",
    "🇫🇷 France (+33)": "+33",
}

# =========================================================
# DEFAULT GOOD DEEDS
# =========================================================

DEFAULT_DEEDS = {
    "🏠 Home": [
        {"name": "Make your bed without being asked", "points": 5},
        {"name": "Keep your room reasonably tidy", "points": 10},
        {"name": "Help set or clear the table", "points": 10},
        {"name": "Help wash dishes or load the dishwasher", "points": 15},
        {"name": "Help with laundry", "points": 15},
        {"name": "Take out the rubbish or recycling", "points": 10},
        {"name": "Help clean a shared area", "points": 15},
        {"name": "Help prepare a meal", "points": 20},
    ],
    "❤️ Family": [
        {"name": "Help a parent without being asked", "points": 20},
        {"name": "Help a sibling with something", "points": 15},
        {"name": "Spend time helping an older family member", "points": 20},

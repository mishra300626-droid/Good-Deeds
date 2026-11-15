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
from datetime import datetime, timedelta

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
        {"name": "Do something thoughtful for a family member", "points": 20},
    ],
    "🤝 Kindness": [
        {"name": "Help someone who is struggling", "points": 20},
        {"name": "Include someone who is being left out", "points": 25},
        {"name": "Give a genuine compliment", "points": 10},
        {"name": "Share something fairly", "points": 10},
        {"name": "Comfort or support someone who is upset", "points": 20},
        {"name": "Do a kind act without expecting a reward", "points": 25},
    ],
    "📚 School & Learning": [
        {"name": "Complete homework responsibly", "points": 10},
        {"name": "Start homework or studying without being reminded", "points": 15},
        {"name": "Help a classmate understand something", "points": 20},
        {"name": "Put real effort into a difficult assignment", "points": 20},
        {"name": "Prepare properly for a test or project", "points": 20},
        {"name": "Read for learning or enjoyment", "points": 10},
        {"name": "Ask for help when genuinely needed", "points": 10},
    ],
    "✅ Responsibility": [
        {"name": "Get ready on time", "points": 10},
        {"name": "Pack your school bag or needed items yourself", "points": 10},
        {"name": "Remember an important responsibility without reminders", "points": 15},
        {"name": "Admit a mistake honestly", "points": 25},
        {"name": "Fix or make up for a mistake", "points": 25},

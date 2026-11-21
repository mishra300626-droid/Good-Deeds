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
        {"name": "Keep a promise or commitment", "points": 20},
    ],
    "🌱 Personal Growth": [
        {"name": "Try something difficult instead of giving up", "points": 20},
        {"name": "Learn a new useful skill", "points": 25},
        {"name": "Stay calm and solve a disagreement respectfully", "points": 25},
        {"name": "Accept helpful feedback well", "points": 15},
        {"name": "Apologise sincerely when appropriate", "points": 20},
        {"name": "Show patience in a difficult situation", "points": 15},
    ],
    "💻 Digital Responsibility": [
        {"name": "Stop screen time when agreed", "points": 10},
        {"name": "Be respectful in messages, games, or social spaces", "points": 15},
        {"name": "Report or avoid harmful online behaviour", "points": 20},
        {"name": "Balance screen time with another useful activity", "points": 10},
    ],
    "🌍 Community": [
        {"name": "Pick up litter safely", "points": 15},
        {"name": "Help a neighbour with an appropriate task", "points": 20},
        {"name": "Donate unused items with a parent", "points": 20},
        {"name": "Help with a school or community activity", "points": 25},
        {"name": "Take care of shared or public spaces", "points": 15},
    ],
    "🐾 Caring": [
        {"name": "Feed or care for a pet responsibly", "points": 10},
        {"name": "Walk or exercise a pet when appropriate", "points": 15},
        {"name": "Help care for plants or a garden", "points": 10},
    ],
    "🛕 Values & Spirituality": [
        {"name": "Go to the temple with family", "points": 15},
        {
            "name": "Take part respectfully in a family spiritual or cultural activity",
            "points": 15,
        },
    ],
    "🎨 Extracurricular": [
        {"name": "Take part in an extracurricular activity", "points": 20},
        {
            "name": "Practise a sport, music, art, dance, or other skill",
            "points": 15,
        },
        {
            "name": "Attend a club, class, team, or activity responsibly",
            "points": 15,
        },
        {"name": "Show good teamwork or sportsmanship", "points": 20},
    ],
    "⭐ Extra Effort": [
        {"name": "Do an important task without being asked", "points": 25},
        {
            "name": "Go beyond what was expected to help someone",
            "points": 30,
        },
        {
            "name": "Show exceptional honesty or responsibility",
            "points": 30,
        },
    ],
}

# =========================================================
# STYLING
# =========================================================

st.markdown(
    """
    <style>
        .login-title {
            text-align: center;
            font-size: 44px;
            font-weight: 800;
            margin-bottom: 0;
        }

        .login-subtitle {
            text-align: center;
            opacity: 0.75;
            margin-top: 4px;
            margin-bottom: 24px;
        }

        .reward-card {
            padding: 18px;
            border-radius: 15px;
            background: #f5f5f5;
            text-align: center;
            margin-bottom: 10px;
            min-height: 205px;
            box-sizing: border-box;
        }

        .reward-card .reward-emoji {
            font-size: 40px;
            margin-bottom: 4px;
        }

        .reward-card .reward-name {
            color: #202124 !important;
            font-size: 21px;
            font-weight: 700;
            line-height: 1.25;
            margin: 10px 0;
        }

        .reward-card .reward-cost {
            color: #333333 !important;
            font-size: 17px;
            font-weight: 700;
        }

        .deed-card {
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 12px;
            background: #f8f9fa;
            border-left: 5px solid #4CAF50;
            color: #202124 !important;
        }

        .deed-card b,
        .deed-card strong,
        .deed-card small {
            color: #202124 !important;
        }

        .badge-card {
            padding: 15px;
            border-radius: 15px;
            background: #f3f3f3;
            color: #202124 !important;
            text-align: center;
            min-height: 100px;
        }

        .badge-card b {
            color: #202124 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# USER SETTINGS
# =========================================================

DEFAULT_SETTINGS = {
    "theme_preset": "Light",
    "timezone": DEFAULT_TIMEZONE,
    "accent_color": "#4F46E5",
    "custom_background": "#FFFFFF",
    "custom_sidebar": "#F8FAFC",
    "custom_card": "#F3F4F6",
    "custom_text": "#1F2937",
    "font_family": "Sans",
    "font_scale": 100,
    "card_radius": 15,
    "card_shadows": True,
    "compact_mode": False,
    "high_contrast": False,
    "reduce_motion": False,
    "large_controls": False,
    "show_progress": True,
    "show_badges": True,
    "show_recent_deeds": True,
    "show_rewards": True,
    "show_motivation": True,
    "motivation_mode": "Growth first",
    "recent_deeds_count": 8,
    "show_account_identifier": True,
    "daily_goal_target": 3,
    "weekly_goal_target": 10,
    "parent_lock_timeout_minutes": 10,
}

SETTINGS_WIDGET_KEYS = [
    "settings_theme_preset",
    "settings_accent_color",
    "settings_font_family",
    "settings_font_scale",
    "settings_card_radius",
    "settings_card_shadows",
    "settings_compact_mode",
    "settings_custom_background",
    "settings_custom_sidebar",
    "settings_custom_card",
    "settings_custom_text",
    "settings_motivation_mode",
    "settings_show_motivation",
    "settings_show_progress",
    "settings_show_badges",
    "settings_show_recent_deeds",
    "settings_recent_deeds_count",
    "settings_show_rewards",
    "settings_high_contrast",
    "settings_large_controls",
    "settings_reduce_motion",
    "settings_show_account_identifier",
    "settings_child_display_name",
    "settings_daily_goal_target",
    "settings_weekly_goal_target",
    "settings_parent_lock_timeout_minutes",
]

THEME_PRESETS = {
    "Light": {
        "background": "#FFFFFF",
        "sidebar": "#F8FAFC",
        "card": "#F3F4F6",
        "text": "#1F2937",
    },
    "Dark": {
        "background": "#0F172A",
        "sidebar": "#111827",
        "card": "#1E293B",
        "text": "#F8FAFC",
    },
    "Warm": {
        "background": "#FFF8EF",
        "sidebar": "#F7E7CE",
        "card": "#FFF0D8",
        "text": "#3B2A20",
    },
    "Cool": {
        "background": "#F4F8FF",
        "sidebar": "#E7EEFA",
        "card": "#EAF1FF",
        "text": "#1E2A3A",
    },
    "Custom": {},
}

FONT_FAMILIES = {
    "Sans": "Arial, Helvetica, sans-serif",
    "Rounded": "'Trebuchet MS', Arial, sans-serif",
    "Serif": "Georgia, 'Times New Roman', serif",
    "Monospace": "Consolas, 'Courier New', monospace",
}

# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "onboarding_replay_version": 0,
    "account_setup_complete": False,
    "account": {
        "login_type": "",
        "identifier": "",
        "country_code": "",
    },
    "setup_complete": False,
    "parent_tour_completed": False,
    "child_name": "",
    "parent_password_hash": "",
    "points": 0,
    "deeds": [],
    "redemptions": [],
    "pending_redemptions": [],
    "reward_request_history": [],
    "pending_deeds": [],
    "child_deed_request_history": [],
    "custom_deeds": [],
    "reflections": [],
    "appreciations": [],
    "settings": DEFAULT_SETTINGS.copy(),
    "rewards": [
        {"name": "Choose a Dessert", "cost": 100, "emoji": "🍰"},
        {"name": "30 Minutes Extra Gaming", "cost": 150, "emoji": "🎮"},
        {"name": "Choose a Movie", "cost": 200, "emoji": "🎬"},
        {"name": "Favourite Restaurant", "cost": 400, "emoji": "🍕"},
        {"name": "Special Family Outing", "cost": 750, "emoji": "🌟"},
    ],
}

# =========================================================
# MULTI-ACCOUNT STORAGE
# =========================================================

def normalize_identifier(identifier):
    """Normalize account identifiers so email/phone lookups are consistent."""
    return str(identifier or "").strip().lower()


def ensure_data_defaults(loaded):
    """Safely upgrade a family's stored data without deleting existing fields."""
    if not isinstance(loaded, dict):
        loaded = copy.deepcopy(DEFAULT_DATA)

    for key, value in DEFAULT_DATA.items():
        if key not in loaded:
            loaded[key] = copy.deepcopy(value)

    if not isinstance(loaded.get("account"), dict):
        loaded["account"] = copy.deepcopy(DEFAULT_DATA["account"])
    for key, value in DEFAULT_DATA["account"].items():
        loaded["account"].setdefault(key, copy.deepcopy(value))

    if not isinstance(loaded.get("settings"), dict):
        loaded["settings"] = copy.deepcopy(DEFAULT_SETTINGS)
    for key, value in DEFAULT_SETTINGS.items():
        loaded["settings"].setdefault(key, copy.deepcopy(value))

    for list_key in (
        "deeds",
        "redemptions",
        "pending_redemptions",
        "reward_request_history",
        "pending_deeds",
        "child_deed_request_history",
        "custom_deeds",
        "reflections",
        "appreciations",
        "rewards",
    ):
        if not isinstance(loaded.get(list_key), list):
            loaded[list_key] = copy.deepcopy(DEFAULT_DATA[list_key])

    return loaded


def get_db_connection():
    """Open the SQLite account database with a reasonable busy timeout."""
    connection = sqlite3.connect(
        ACCOUNTS_DB_FILE,
        timeout=30,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def init_accounts_db():
    """Create the account table if it does not exist yet."""
    connection = get_db_connection()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS family_accounts (
                identifier TEXT PRIMARY KEY,
                login_type TEXT NOT NULL,
                country_code TEXT NOT NULL DEFAULT '',
                family_data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def account_exists(identifier):
    """Return True if a family account is registered for this identifier."""
    normalized = normalize_identifier(identifier)
    if not normalized:
        return False

    connection = get_db_connection()
    try:
        row = connection.execute(
            "SELECT 1 FROM family_accounts WHERE identifier = ?",
            (normalized,),
        ).fetchone()
        return row is not None
    finally:
        connection.close()


def load_account_data(identifier):
    """Load one family's data from the database, or None if not registered."""
    normalized = normalize_identifier(identifier)
    connection = get_db_connection()
    try:
        row = connection.execute(
            "SELECT family_data FROM family_accounts WHERE identifier = ?",
            (normalized,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return None

    try:
        loaded = json.loads(row["family_data"])
    except (json.JSONDecodeError, TypeError, ValueError):
        return copy.deepcopy(DEFAULT_DATA)

    return ensure_data_defaults(loaded)


def save_account_record(identifier, family_data):
    """Persist one family's data without touching any other family's record."""
    normalized = normalize_identifier(identifier)
    account = family_data.get("account", {}) if isinstance(family_data, dict) else {}
    login_type = str(account.get("login_type", "email") or "email")
    country_code = str(account.get("country_code", "") or "")
    serialized = json.dumps(
        family_data,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    connection = get_db_connection()
    try:
        connection.execute(
            """
            INSERT INTO family_accounts
                (identifier, login_type, country_code, family_data, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(identifier) DO UPDATE SET
                login_type = excluded.login_type,
                country_code = excluded.country_code,
                family_data = excluded.family_data,
                updated_at = CURRENT_TIMESTAMP
            """,
            (normalized, login_type, country_code, serialized),
        )
        connection.commit()
    finally:
        connection.close()


def create_family_account(identifier, login_type, country_code):
    """Create a fresh, isolated family profile if the identifier is unused."""
    normalized = normalize_identifier(identifier)
    new_data = copy.deepcopy(DEFAULT_DATA)
    new_data["account_setup_complete"] = True
    new_data["onboarding_replay_version"] = ONBOARDING_REPLAY_VERSION
    new_data["account"] = {
        "login_type": str(login_type),
        "identifier": normalized,
        "country_code": str(country_code or ""),
    }

    connection = get_db_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT 1 FROM family_accounts WHERE identifier = ?",
            (normalized,),
        ).fetchone()

        if existing is not None:
            connection.rollback()
            return False, None

        serialized = json.dumps(
            new_data,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        connection.execute(
            """
            INSERT INTO family_accounts
                (identifier, login_type, country_code, family_data)
            VALUES (?, ?, ?, ?)
            """,
            (
                normalized,
                str(login_type),
                str(country_code or ""),
                serialized,
            ),
        )
        connection.commit()
        return True, new_data

    except sqlite3.IntegrityError:
        connection.rollback()
        return False, None
    finally:
        connection.close()


def load_legacy_data():
    """Read the old single-family JSON file only for migration."""
    if not os.path.exists(DATA_FILE):
        return None

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)
        if not isinstance(loaded, dict):
            return None
        return ensure_data_defaults(loaded)
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return None


def migrate_legacy_account():
    """Migrate the old family JSON record if it has a usable account identifier."""
    legacy = load_legacy_data()
    if not legacy:
        return

    identifier = normalize_identifier(
        legacy.get("account", {}).get("identifier", "")
    )
    if not identifier or account_exists(identifier):
        return

    # Keep the existing family history/settings intact during migration.
    legacy["account"]["identifier"] = identifier
    save_account_record(identifier, legacy)


def save_data(data_to_save):
    """Save changes to the currently signed-in family's database record."""
    active_identifier = normalize_identifier(
        st.session_state.get("active_identifier", "")
    )
    if not active_identifier:
        raise RuntimeError(
            "Cannot save family data because no account is signed in."
        )
    save_account_record(active_identifier, data_to_save)


init_accounts_db()
migrate_legacy_account()

if "data" not in st.session_state:
    st.session_state.data = copy.deepcopy(DEFAULT_DATA)

if "active_identifier" not in st.session_state:
    st.session_state.active_identifier = ""

data = st.session_state.data

# Clear settings widget state only at the beginning of a rerun, before those
# widgets are created. This makes the Reset Settings button actually reset UI.
if st.session_state.pop("_reset_settings_widgets_pending", False):
    for _widget_key in SETTINGS_WIDGET_KEYS:
        st.session_state.pop(_widget_key, None)

# Make settings compatible with older saved data without deleting anything.
if "settings" not in data or not isinstance(data["settings"], dict):
    data["settings"] = DEFAULT_SETTINGS.copy()

for setting_key, setting_value in DEFAULT_SETTINGS.items():
    if setting_key not in data["settings"]:
        data["settings"][setting_key] = setting_value


def valid_hex_color(value, fallback):
    if isinstance(value, str) and re.fullmatch(
        r"#[0-9A-Fa-f]{6}",
        value,
    ):
        return value
    return fallback


def safe_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _hex_rgb(value):
    """Convert a #RRGGBB colour into an RGB tuple."""
    value = valid_hex_color(value, "#000000").lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _relative_luminance(value):
    """Calculate WCAG relative luminance for a hex colour."""
    channels = []
    for channel in _hex_rgb(value):
        normalized = channel / 255.0
        channels.append(
            normalized / 12.92
            if normalized <= 0.04045
            else ((normalized + 0.055) / 1.055) ** 2.4
        )
    return (
        0.2126 * channels[0]
        + 0.7152 * channels[1]
        + 0.0722 * channels[2]
    )


def _contrast_ratio(first, second):
    """Return the WCAG contrast ratio between two hex colours."""
    lum1 = _relative_luminance(first)
    lum2 = _relative_luminance(second)
    lighter, darker = max(lum1, lum2), min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def _readable_text(preferred, background):
    """Keep a chosen text colour when readable; otherwise use black or white."""
    if _contrast_ratio(preferred, background) >= 4.5:
        return preferred
    black = "#111827"
    white = "#FFFFFF"
    return black if _contrast_ratio(black, background) >= _contrast_ratio(white, background) else white


def apply_saved_appearance():
    settings = data["settings"]
    preset_name = settings.get("theme_preset", "Light")

    if preset_name == "Custom":
        background = valid_hex_color(settings.get("custom_background"), "#FFFFFF")
        sidebar = valid_hex_color(settings.get("custom_sidebar"), "#F8FAFC")
        card = valid_hex_color(settings.get("custom_card"), "#F3F4F6")
        preferred_text = valid_hex_color(settings.get("custom_text"), "#1F2937")
    else:
        preset = THEME_PRESETS.get(preset_name, THEME_PRESETS["Light"])
        background = preset["background"]
        sidebar = preset["sidebar"]
        card = preset["card"]
        preferred_text = preset["text"]

    accent = valid_hex_color(settings.get("accent_color"), "#4F46E5")

    if settings.get("high_contrast", False):
        if preset_name == "Dark":
            background, sidebar, card, preferred_text = "#000000", "#000000", "#111111", "#FFFFFF"
        else:
            background, sidebar, card, preferred_text = "#FFFFFF", "#FFFFFF", "#FFFFFF", "#000000"

    # Check contrast separately for the page, sidebar, cards/fields and accent buttons.
    text_main = _readable_text(preferred_text, background)
    text_sidebar = _readable_text(preferred_text, sidebar)
    text_card = _readable_text(preferred_text, card)
    text_accent = _readable_text("#FFFFFF", accent)
    if _contrast_ratio(text_accent, accent) < 4.5:
        text_accent = _readable_text("#111827", accent)

    font_family = FONT_FAMILIES.get(settings.get("font_family", "Sans"), FONT_FAMILIES["Sans"])
    font_scale = safe_int(settings.get("font_scale", 100), 100, 85, 130)
    radius = safe_int(settings.get("card_radius", 15), 15, 0, 30)
    compact = bool(settings.get("compact_mode", False))
    large_controls = bool(settings.get("large_controls", False))
    reduce_motion = bool(settings.get("reduce_motion", False))
    shadows = bool(settings.get("card_shadows", True))

    block_gap = "0.45rem" if compact else "1rem"
    button_height = "3.1rem" if large_controls else "2.75rem"
    input_height = "3.1rem" if large_controls else "2.75rem"
    shadow_css = "0 6px 18px rgba(0,0,0,0.14)" if shadows else "none"
    motion_css = (
        "*, *::before, *::after { animation-duration: 0.001ms !important; "
        "animation-iteration-count: 1 !important; transition-duration: 0.001ms !important; "
        "scroll-behavior: auto !important; }"
        if reduce_motion else ""
    )

    # This stylesheet deliberately avoids global '* { color: ... }' rules.
    # Those rules were overriding widget states, button labels and placeholders.
    st.markdown(
        f"""
        <style>
          :root {{
            --gd-accent: {accent};
            --gd-bg: {background};
            --gd-sidebar: {sidebar};
            --gd-card: {card};
            --gd-text: {text_main};
            --gd-sidebar-text: {text_sidebar};
            --gd-card-text: {text_card};
            --gd-accent-text: {text_accent};
            --gd-radius: {radius}px;
          }}

          html, body, [class*="css"] {{ font-family: {font_family} !important; }}
          .stApp, [data-testid="stAppViewContainer"] {{
            background: var(--gd-bg) !important;
            color: var(--gd-text) !important;
            font-size: {font_scale}% !important;
          }}
          [data-testid="stSidebar"], [data-testid="stSidebar"] > div {{
            background: var(--gd-sidebar) !important;
            color: var(--gd-sidebar-text) !important;
          }}

          /* Normal page copy and headings */
          .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
          .stApp p, .stApp li, .stApp label,
          .stApp [data-testid="stMarkdownContainer"],
          .stApp [data-testid="stCaptionContainer"],
          .stApp [data-testid="stWidgetLabel"] {{
            color: var(--gd-text) !important;
          }}
          [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
          [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p,
          [data-testid="stSidebar"] label,
          [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
          [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
            color: var(--gd-sidebar-text) !important;
          }}

          /* Cards, expanders, dialogs and popovers */
          [data-testid="stVerticalBlockBorderWrapper"] > div,
          [data-testid="stExpander"] details,
          [data-testid="stDialog"] > div,
          [data-testid="stPopover"] [data-testid="stPopoverContent"] {{
            background: var(--gd-card) !important;
            color: var(--gd-card-text) !important;
            border-color: color-mix(in srgb, var(--gd-card-text) 25%, transparent) !important;
          }}

          /* Inputs and select controls — explicitly style the actual text field. */
          input, textarea,
          [data-baseweb="input"] input,
          [data-baseweb="textarea"] textarea,
          [data-baseweb="select"] > div,
          [data-baseweb="select"] input {{
            background: var(--gd-card) !important;
            color: var(--gd-card-text) !important;
            -webkit-text-fill-color: var(--gd-card-text) !important;
            border-color: color-mix(in srgb, var(--gd-card-text) 30%, transparent) !important;
            opacity: 1 !important;
          }}
          input::placeholder, textarea::placeholder,
          [data-baseweb="input"] input::placeholder,
          [data-baseweb="textarea"] textarea::placeholder {{
            color: color-mix(in srgb, var(--gd-card-text) 75%, transparent) !important;
            -webkit-text-fill-color: color-mix(in srgb, var(--gd-card-text) 75%, transparent) !important;
            opacity: 1 !important;
          }}
          [data-baseweb="popover"], [data-baseweb="menu"],
          [role="listbox"], [role="option"] {{
            background: var(--gd-card) !important;
            color: var(--gd-card-text) !important;
          }}
          [role="option"] *, [role="listbox"] * {{ color: var(--gd-card-text) !important; }}

          /* Radio buttons, checkboxes and their labels */
          [data-testid="stRadio"] label, [data-testid="stCheckbox"] label,
          [data-testid="stSelectbox"] label, [data-testid="stTextInput"] label,
          [data-testid="stTextArea"] label, [data-testid="stNumberInput"] label,
          [data-testid="stDateInput"] label, [data-testid="stTimeInput"] label {{
            color: var(--gd-text) !important;
          }}

          /* Alerts and status messages */
          [data-testid="stAlert"] {{
            background: var(--gd-card) !important;
            border: 1px solid color-mix(in srgb, var(--gd-card-text) 28%, transparent) !important;
            border-radius: var(--gd-radius) !important;
          }}
          [data-testid="stAlert"] p, [data-testid="stAlert"] span,
          [data-testid="stAlert"] div, [data-testid="stAlert"] li {{
            color: var(--gd-card-text) !important;
          }}

          /* All buttons, including disabled buttons, must retain readable labels. */
          div.stButton > button, div.stDownloadButton > button,
          [data-testid="stFormSubmitButton"] button {{
            color: var(--gd-card-text) !important;
            -webkit-text-fill-color: var(--gd-card-text) !important;
            background: var(--gd-card) !important;
            border: 1px solid color-mix(in srgb, var(--gd-card-text) 35%, transparent) !important;
            border-radius: var(--gd-radius) !important;
            min-height: {button_height} !important;
            font-weight: 650 !important;
            opacity: 1 !important;
            filter: none !important;
          }}
          div.stButton > button:disabled,
          div.stDownloadButton > button:disabled,
          [data-testid="stFormSubmitButton"] button:disabled,
          div.stButton > button[aria-disabled="true"] {{
            color: var(--gd-card-text) !important;
            -webkit-text-fill-color: var(--gd-card-text) !important;
            background: var(--gd-card) !important;
            opacity: 1 !important;
            filter: none !important;
            cursor: not-allowed !important;
          }}
          div.stButton > button[kind="primary"],
          [data-testid="stFormSubmitButton"] button[kind="primary"] {{
            color: var(--gd-accent-text) !important;
            -webkit-text-fill-color: var(--gd-accent-text) !important;
            background: var(--gd-accent) !important;
            border-color: var(--gd-accent) !important;
          }}
          div.stButton > button[kind="primary"] *,
          [data-testid="stFormSubmitButton"] button[kind="primary"] * {{
            color: var(--gd-accent-text) !important;
            -webkit-text-fill-color: var(--gd-accent-text) !important;
          }}
          a, a * {{ color: var(--gd-accent) !important; }}

          /* Metrics, tables and app-created cards */
          [data-testid="stMetric"], [data-testid="stTable"],
          [data-testid="stDataFrame"], .reward-card, .deed-card, .badge-card {{
            background: var(--gd-card) !important;
            color: var(--gd-card-text) !important;
            border-radius: var(--gd-radius) !important;
            box-shadow: {shadow_css} !important;
          }}
          .reward-card *, .deed-card *, .badge-card *,
          [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
            color: var(--gd-card-text) !important;
          }}

          /* Gear settings button and keyboard focus */
          [data-testid="stPopover"] > button,
          [data-testid="stPopover"] button {{
            background: var(--gd-card) !important;
            color: var(--gd-card-text) !important;
            border: 1px solid color-mix(in srgb, var(--gd-card-text) 30%, transparent) !important;
          }}
          :focus-visible {{ outline: 3px solid var(--gd-accent) !important; outline-offset: 3px !important; }}

          /* Locked screen and tour cards remain readable while respecting the theme. */
          .gd-locked-message {{
            background: var(--gd-card) !important;
            color: var(--gd-card-text) !important;
            border: 1px solid color-mix(in srgb, var(--gd-card-text) 28%, transparent) !important;
            padding: 1rem !important;
            border-radius: var(--gd-radius) !important;
          }}
          .gd-locked-message * {{ color: var(--gd-card-text) !important; }}
          .gd-tour-text {{
            background: var(--gd-card) !important;
            color: var(--gd-card-text) !important;
            border: 2px solid color-mix(in srgb, var(--gd-card-text) 35%, transparent) !important;
            border-radius: 12px !important;
            padding: 16px 18px !important;
            font-size: 1.08rem !important;
            line-height: 1.7 !important;
            font-weight: 600 !important;
            opacity: 1 !important;
          }}
          .gd-tour-text * {{ color: var(--gd-card-text) !important; opacity: 1 !important; }}
          .gd-tour-bullets ul {{ margin: 0.2rem 0 0.2rem 1.2rem !important; padding-left: 1rem !important; }}
          .gd-tour-bullets li {{ margin-bottom: 0.65rem !important; }}

          [data-testid="stVerticalBlock"] {{ gap: {block_gap}; }}
          [data-testid="stTabs"] button {{ border-radius: 10px 10px 0 0 !important; font-weight: 650 !important; }}
          @media (max-width: 768px) {{
            [data-testid="stMetric"] {{ padding: 0.6rem 0.7rem !important; }}
            [data-testid="stMetricValue"] {{ font-size: 1.15rem !important; }}
            div[data-testid="stHorizontalBlock"] {{ gap: 0.55rem !important; }}
          }}
          {motion_css}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_saved_appearance()

# =========================================================
# LEGACY ONBOARDING REPLAY REMOVED
# =========================================================
# The old replay logic reset the single global account profile. In a
# multi-account app, onboarding is tracked independently within each family
# record, so this global reset must not run.

# =========================================================
# SECURITY HELPERS
# =========================================================

def hash_parent_password(password):
    """Hash parent passwords with salted PBKDF2 (with legacy compatibility)."""
    iterations = 310_000
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def check_parent_password(password):
    """Verify new PBKDF2 hashes and upgrade old SHA-256 hashes on success."""
    stored_hash = str(data.get("parent_password_hash", "") or "")
    if not stored_hash:
        return False

    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            algorithm, iterations_text, salt_hex, digest_hex = stored_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iterations_text)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                str(password).encode("utf-8"),
                salt,
                iterations,
            )
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    # Existing accounts used a plain SHA-256 hash. Verify it, then upgrade it.
    legacy_digest = hashlib.sha256(str(password).encode("utf-8")).hexdigest()
    if hmac.compare_digest(legacy_digest, stored_hash):
        data["parent_password_hash"] = hash_parent_password(password)
        save_data(data)
        return True
    return False


def valid_email(email):
    return (
        re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email.strip(),
        )
        is not None
    )


def clean_phone(phone):
    return re.sub(r"\D", "", phone)


def generate_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def issue_otp(identifier):
    otp = generate_otp()

    st.session_state.otp_identifier = identifier
    st.session_state.otp_hash = hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()

    st.session_state.otp_expires_at = (
        time.time() + OTP_VALID_SECONDS
    )

    st.session_state.otp_attempts = 0

    # DEVELOPMENT MODE:
    # In a production app, replace this with an email/SMS provider.
    st.session_state.demo_otp = otp


def verify_otp(identifier, entered_otp):
    if identifier != st.session_state.get(
        "otp_identifier",
        "",
    ):
        return False, "This OTP was created for a different account."

    if time.time() > st.session_state.get(
        "otp_expires_at",
        0,
    ):
        return False, "That OTP has expired. Request a new one."

    attempts = st.session_state.get(
        "otp_attempts",
        0,
    )

    if attempts >= 5:
        return (
            False,
            "Too many incorrect attempts. Request a new OTP.",
        )

    st.session_state.otp_attempts = attempts + 1

    entered_hash = hashlib.sha256(
        entered_otp.strip().encode("utf-8")
    ).hexdigest()

    expected_hash = st.session_state.get(
        "otp_hash",
        "",
    )

    if hmac.compare_digest(
        entered_hash,
        expected_hash,
    ):
        return True, ""

    return False, "Incorrect OTP."


def clear_otp():
    for key in [
        "otp_identifier",
        "otp_hash",
        "otp_expires_at",
        "otp_attempts",
        "demo_otp",
    ]:
        st.session_state.pop(
            key,
            None,
        )

# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "parent_authenticated" not in st.session_state:
    st.session_state.parent_authenticated = False

if "parent_last_activity" not in st.session_state:
    st.session_state.parent_last_activity = 0.0

if "auth_stage" not in st.session_state:
    st.session_state.auth_stage = "identifier"

# =========================================================
# SIGN IN / SIGN UP WITH OTP
# =========================================================

if not st.session_state.logged_in:

    st.markdown(
        '<div class="login-title">⭐ Good Deeds</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="login-subtitle">'
        "Sign in to your family account or create a new one"
        "</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        "Prototype notice: OTP codes are currently generated and displayed "
        "inside the app. This is not real email/SMS verification."
    )

    left, centre, right = st.columns([1, 1.5, 1])

    with centre:

        if st.session_state.auth_stage == "identifier":

            auth_mode = st.radio(
                "Welcome",
                ["Sign In", "Sign Up"],
                horizontal=True,
                key="auth_mode",
            )

            st.subheader(
                "Sign in to your account"
                if auth_mode == "Sign In"
                else "Create a new family account"
            )

            login_type = st.radio(
                "Continue using",
                ["📧 Email address", "📱 Phone number"],
                horizontal=True,
                key=f"auth_login_type_{auth_mode}",
            )

            if login_type == "📧 Email address":

                email = st.text_input(
                    "Email address",
                    placeholder="parent@example.com",
                    key=f"auth_email_{auth_mode}",
                )

                identifier = normalize_identifier(email)
                country_code = ""
                chosen_type = "email"

            else:

                labels = list(COUNTRY_CODES.keys())
                country_label = st.selectbox(
                    "Country / region",
                    labels,
                    index=0,
                    key=f"auth_country_{auth_mode}",
                )

                country_code = COUNTRY_CODES[country_label]

                c1, c2 = st.columns([1, 3])

                with c1:
                    st.text_input(
                        "Code",
                        value=country_code,
                        disabled=True,
                        key=f"auth_country_code_display_{auth_mode}",
                    )

                with c2:
                    phone = st.text_input(
                        "Phone number",
                        placeholder="9876543210",
                        key=f"auth_phone_{auth_mode}",
                    )

                identifier = normalize_identifier(
                    country_code + clean_phone(phone)
                )
                chosen_type = "phone"

            button_label = (
                "Send Sign-In OTP"
                if auth_mode == "Sign In"
                else "Create Account & Send OTP"
            )

            if st.button(
                button_label,
                type="primary",
                use_container_width=True,
            ):

                if chosen_type == "email":

                    if not valid_email(identifier):
                        st.error("Please enter a valid email address.")
                        st.stop()

                else:

                    digits = clean_phone(identifier)

                    if len(digits) < 8 or len(digits) > 15:
                        st.error("Please enter a valid phone number.")
                        st.stop()

                registered = account_exists(identifier)

                if auth_mode == "Sign Up" and registered:
                    st.error(
                        "An account with this email/phone already exists. "
                        "Please choose Sign In."
                    )
                    st.stop()

                if auth_mode == "Sign In" and not registered:
                    st.error(
                        "No account was found for this email/phone. "
                        "Please choose Sign Up to create one."
                    )
                    st.stop()

                st.session_state.pending_identifier = identifier
                st.session_state.pending_login_type = chosen_type
                st.session_state.pending_country_code = country_code
                st.session_state.pending_auth_mode = auth_mode

                issue_otp(identifier)

                st.session_state.auth_stage = "otp"
                st.rerun()

        else:

            identifier = st.session_state.get(
                "pending_identifier",
                "",
            )
            pending_auth_mode = st.session_state.get(
                "pending_auth_mode",
                "Sign In",
            )

            st.subheader(
                "Verify your sign-up code"
                if pending_auth_mode == "Sign Up"
                else "Enter your sign-in code"
            )

            st.write(
                f"A six-digit demo code was generated for **{identifier}**."
            )

            st.warning(
                "🧪 Demo OTP: the code is shown below because this app "
                "is not connected to an email or SMS provider yet. "
                "Do not treat this as secure identity verification."
            )

            st.code(
                st.session_state.get(
                    "demo_otp",
                    "------",
                )
            )

            entered_otp = st.text_input(
                "6-digit OTP",
                max_chars=6,
                placeholder="123456",
                key="entered_otp",
            )

            if st.button(
                "Verify OTP",
                type="primary",
                use_container_width=True,
            ):

                success, message = verify_otp(
                    identifier,
                    entered_otp,
                )

                if success:

                    if pending_auth_mode == "Sign Up":

                        created, new_family_data = create_family_account(
                            identifier,
                            st.session_state.get(
                                "pending_login_type",
                                "email",
                            ),
                            st.session_state.get(
                                "pending_country_code",
                                "",
                            ),
                        )

                        if not created:
                            st.error(
                                "This account was registered already. "
                                "Please return and choose Sign In."
                            )
                            st.stop()

                        st.session_state.active_identifier = identifier
                        st.session_state.data = new_family_data

                    else:

                        existing_family_data = load_account_data(identifier)

                        if existing_family_data is None:
                            st.error(
                                "This account could not be loaded. "
                                "Please try again."
                            )
                            st.stop()

                        st.session_state.active_identifier = identifier
                        st.session_state.data = existing_family_data

                    st.session_state.logged_in = True
                    st.session_state.parent_authenticated = False
                    st.session_state.parent_last_activity = 0.0
                    st.session_state["dashboard_mode"] = "👦 Child Dashboard"
                    st.session_state["parent_tour_step"] = 0
                    st.session_state.auth_stage = "identifier"

                    clear_otp()
                    st.rerun()

                else:
                    st.error(message)

            b1, b2 = st.columns(2)

            with b1:
                if st.button(
                    "Send new OTP",
                    use_container_width=True,
                ):
                    issue_otp(identifier)
                    st.rerun()

            with b2:
                if st.button(
                    "Change email / phone",
                    use_container_width=True,
                ):
                    clear_otp()
                    st.session_state.auth_stage = "identifier"
                    st.rerun()

    st.stop()
# =========================================================
# FIRST-TIME PARENT SETUP
# =========================================================

if (
    not data.get("setup_complete", False)
    or not data.get("parent_password_hash")
):

    st.title("👨‍👩‍👦 Parent Setup")

    st.info(
        "Your family account has been created. A parent or guardian "
        "should set up the child's profile and create the separate "
        "Parent Dashboard password."
    )

    with st.form(
        "first_time_parent_setup"
    ):

        child_name = st.text_input(
            "Child's name",
            value=data.get(
                "child_name",
                "",
            ),
        )

        timezone_choice = st.selectbox(
            "Your family's timezone",
            AVAILABLE_TIMEZONES,
            index=AVAILABLE_TIMEZONES.index(DEFAULT_TIMEZONE),
            help="All dates and times in the app will use this timezone.",
        )

        parent_password = st.text_input(
            "Create Parent Dashboard Password",
            type="password",
        )

        confirm_parent_password = st.text_input(
            "Confirm Parent Dashboard Password",
            type="password",
        )

        submitted = st.form_submit_button(
            "🔐 Finish Parent Setup"
        )

        if submitted:

            if not child_name.strip():

                st.error(
                    "Please enter the child's name."
                )

            elif len(parent_password) < 8:

                st.error(
                    "Please choose a Parent Dashboard password "
                    "with at least 8 characters."
                )

            elif parent_password != confirm_parent_password:

                st.error(
                    "The two Parent Dashboard passwords do not match."
                )

            else:

                data["child_name"] = child_name.strip()
                data.setdefault("settings", {})["timezone"] = timezone_choice

                data["parent_password_hash"] = (
                    hash_parent_password(
                        parent_password
                    )
                )

                data["setup_complete"] = True

                save_data(data)

                st.session_state.parent_authenticated = True
                st.session_state.parent_last_activity = time.time()
                st.session_state["dashboard_mode"] = "👨‍👩‍👦 Parent Dashboard"
                st.session_state["parent_tour_step"] = 0

                st.success(
                    "✅ Parent setup complete."
                )

                st.rerun()

    st.stop()

# =========================================================
# APP HELPERS
# =========================================================

def get_level(points):

    if points < 100:
        return "🌱 Beginner"

    elif points < 300:
        return "🌟 Good Helper"

    elif points < 600:
        return "🏅 Super Helper"

    elif points < 1000:
        return "🏆 Champion"

    elif points < 2000:
        return "👑 Role Model"

    else:
        return "💎 Legend"


def parse_deed_datetime(value):
    """Parse the date formats used by current and older deed records."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
        for date_format in (
            "%d %b %Y, %I:%M %p",
            "%d %b %Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                continue
    return None


def get_progress_summary():
    """Calculate deed activity, goals, streaks and chart series from history."""
    today = now_local().date()
    week_start = today - timedelta(days=today.weekday())
    parsed_dates = []
    total_points_earned = 0

    for deed in data.get("deeds", []):
        parsed = parse_deed_datetime(deed.get("date", ""))
        if parsed:
            parsed_dates.append(parsed.date())
        total_points_earned += safe_int(deed.get("points", 0), 0, 0, 1_000_000)

    date_counts = {}
    weekday_counts = {}
    for deed_date in parsed_dates:
        date_counts[deed_date] = date_counts.get(deed_date, 0) + 1
        weekday_counts[deed_date.weekday()] = weekday_counts.get(deed_date.weekday(), 0) + 1

    today_count = date_counts.get(today, 0)
    week_count = sum(
        count for deed_date, count in date_counts.items()
        if week_start <= deed_date <= today
    )
    active_days = len(date_counts)

    streak_cursor = today if today in date_counts else today - timedelta(days=1)
    current_streak = 0
    if streak_cursor in date_counts:
        while streak_cursor in date_counts:
            current_streak += 1
            streak_cursor -= timedelta(days=1)

    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if weekday_counts:
        max_weekday_count = max(weekday_counts.values())
        most_consistent_day = next(
            weekday_names[index]
            for index in range(7)
            if weekday_counts.get(index, 0) == max_weekday_count
        )
        most_consistent_count = max_weekday_count
    else:
        most_consistent_day = "—"
        most_consistent_count = 0

    daily_goal = safe_int(data.get("settings", {}).get("daily_goal_target", 3), 3, 1, 20)
    weekly_goal = safe_int(data.get("settings", {}).get("weekly_goal_target", 10), 10, 1, 100)
    last_7_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    last_30_days = [today - timedelta(days=offset) for offset in range(29, -1, -1)]

    return {
        "today": today,
        "today_count": today_count,
        "week_count": week_count,
        "daily_goal": daily_goal,
        "weekly_goal": weekly_goal,
        "current_streak": current_streak,
        "active_days": active_days,
        "total_points_earned": total_points_earned,
        "most_consistent_day": most_consistent_day,
        "most_consistent_count": most_consistent_count,
        "last_7_days": last_7_days,
        "last_7_counts": [date_counts.get(day, 0) for day in last_7_days],
        "last_30_days": last_30_days,
        "last_30_counts": [date_counts.get(day, 0) for day in last_30_days],
    }


def submit_child_deed(name, category, suggested_points, description=""):
    """Queue a child's deed for parent review without awarding points yet."""
    request = {
        "request_id": secrets.token_hex(8),
        "name": str(name).strip(),
        "category": str(category).strip(),
        "suggested_points": safe_int(suggested_points, 0, 0, 1_000_000),
        "description": str(description or "").strip(),
        "submitted_at": now_local().strftime("%d %b %Y, %I:%M %p"),
    }
    data.setdefault("pending_deeds", []).insert(0, request)
    save_data(data)
    return request


def approve_child_deed(request_id, is_extra_effort=False):
    request = next(
        (item for item in data.get("pending_deeds", []) if item.get("request_id") == request_id),
        None,
    )
    if request is None:
        return False, 0

    awarded_points = add_deed(
        request.get("name", "Good deed"),
        request.get("category", "Uncategorised"),
        request.get("suggested_points", 0),
        request.get("description", ""),
        is_extra_effort=bool(is_extra_effort),
    )
    data["pending_deeds"] = [
        item for item in data.get("pending_deeds", [])
        if item.get("request_id") != request_id
    ]
    data.setdefault("child_deed_request_history", []).insert(0, {
        **request,
        "status": "Approved",
        "reviewed_at": now_local().strftime("%d %b %Y, %I:%M %p"),
        "awarded_points": awarded_points,
    })
    save_data(data)
    return True, awarded_points


def reject_child_deed(request_id, reason=""):
    request = next(
        (item for item in data.get("pending_deeds", []) if item.get("request_id") == request_id),
        None,
    )
    if request is None:
        return False
    data["pending_deeds"] = [
        item for item in data.get("pending_deeds", [])
        if item.get("request_id") != request_id
    ]
    data.setdefault("child_deed_request_history", []).insert(0, {
        **request,
        "status": "Needs another try" if reason.strip() else "Not approved",
        "reviewed_at": now_local().strftime("%d %b %Y, %I:%M %p"),
        "review_note": str(reason or "").strip(),
    })
    save_data(data)
    return True


def approve_reward_request(request_id):
    request = next(
        (item for item in data.get("pending_redemptions", []) if item.get("request_id") == request_id),
        None,
    )
    if request is None:
        return False, "This reward request was not found."

    cost = safe_int(request.get("cost", 0), 0, 0, 1_000_000)
    current_points = safe_int(data.get("points", 0), 0, 0, 10_000_000)
    if cost <= 0 or current_points < cost:
        return False, "The current points balance is not enough to approve this request."

    approved_at = now_local().strftime("%d %b %Y, %I:%M %p")
    data["points"] = current_points - cost
    data.setdefault("redemptions", []).insert(0, {
        "request_id": request_id,
        "reward": str(request.get("reward", "Reward")),
        "cost": cost,
        "requested_at": request.get("requested_at", ""),
        "date": approved_at,
        "status": "Approved",
    })
    data["pending_redemptions"] = [
        item for item in data.get("pending_redemptions", [])
        if item.get("request_id") != request_id
    ]
    data.setdefault("reward_request_history", []).insert(0, {
        **request,
        "status": "Approved",
        "reviewed_at": approved_at,
    })
    save_data(data)
    return True, "Approved"


def reject_reward_request(request_id, reason=""):
    request = next(
        (item for item in data.get("pending_redemptions", []) if item.get("request_id") == request_id),
        None,
    )
    if request is None:
        return False
    data["pending_redemptions"] = [
        item for item in data.get("pending_redemptions", [])
        if item.get("request_id") != request_id
    ]
    data.setdefault("reward_request_history", []).insert(0, {
        **request,
        "status": "Not approved",
        "reviewed_at": now_local().strftime("%d %b %Y, %I:%M %p"),
        "review_note": str(reason or "").strip(),
    })
    save_data(data)
    return True


def get_badges():
    """Badges celebrate participation and variety, not money earned."""
    badges = []
    deeds = data.get("deeds", [])

    if len(deeds) >= 1:
        badges.append(("🌱", "First Good Deed"))
    if len(deeds) >= 5:
        badges.append(("⭐", "5 Good Deeds Recorded"))
    if len(deeds) >= 10:
        badges.append(("🏆", "10 Good Deeds Recorded"))
    if len(deeds) >= 25:
        badges.append(("👑", "25 Good Deeds Recorded"))

    categories = {
        deed.get("category", "")
        for deed in deeds
        if deed.get("category")
    }
    if len(categories) >= 3:
        badges.append(("🌍", "A Variety of Good Deeds"))

    reflections = data.get("reflections", [])
    if len(reflections) >= 1:
        badges.append(("🪞", "First Reflection"))
    if len(reflections) >= 5:
        badges.append(("🌿", "Thoughtful Reflector"))

    streak = get_progress_summary().get("current_streak", 0)
    if streak >= 3:
        badges.append(("🔥", "3-Day Kindness Streak"))
    if streak >= 7:
        badges.append(("⚡", "7-Day Kindness Streak"))
    if streak >= 14:
        badges.append(("💫", "14-Day Kindness Streak"))
    if streak >= 30:
        badges.append(("🌈", "30-Day Kindness Streak"))

    return badges


def add_deed(
    name,
    category,
    suggested_points,
    description="",
    is_extra_effort=False,
):
    """Record a deed and award points only under the chosen family rules.

    Existing point balances/history are preserved. New deeds in Growth first
    and No points modes do not add points. Extra effort only requires the
    parent to explicitly mark the deed as voluntary extra effort.
    """
    try:
        suggested_points = max(0, int(suggested_points))
    except (TypeError, ValueError):
        suggested_points = 0

    motivation_mode = data.get("settings", {}).get(
        "motivation_mode", "Growth first"
    )

    if motivation_mode == "Points for every deed":
        awarded_points = suggested_points
    elif motivation_mode == "Extra effort only" and is_extra_effort:
        awarded_points = suggested_points
    else:
        awarded_points = 0

    new_deed = {
        "name": str(name).strip(),
        "category": str(category).strip(),
        "points": awarded_points,
        "suggested_points": suggested_points,
        "extra_effort": bool(is_extra_effort),
        "points_mode": motivation_mode,
        "description": str(description or "").strip(),
        "date": now_local().strftime("%d %b %Y, %I:%M %p"),
    }

    data.setdefault("deeds", []).insert(0, new_deed)
    try:
        current_points = max(0, int(data.get("points", 0)))
    except (TypeError, ValueError):
        current_points = 0
    data["points"] = current_points + awarded_points
    save_data(data)
    return awarded_points


def redeem_reward(reward):
    """Submit a reward request; points are deducted only after parent approval."""
    try:
        current_points = safe_int(data.get("points", 0), 0, 0, 10_000_000)
        reward_cost = safe_int(reward.get("cost", 0), 0, 0, 1_000_000)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False

    reserved_points = sum(
        safe_int(item.get("cost", 0), 0, 0, 1_000_000)
        for item in data.get("pending_redemptions", [])
    )
    available_points = max(0, current_points - reserved_points)
    if reward_cost <= 0 or available_points < reward_cost:
        return False

    request = {
        "request_id": secrets.token_hex(8),
        "reward": str(reward.get("name", "Reward")),
        "cost": reward_cost,
        "requested_at": now_local().strftime("%d %b %Y, %I:%M %p"),
        "status": "Pending",
    }
    data.setdefault("pending_redemptions", []).insert(0, request)
    save_data(data)
    return True


def get_all_deeds_by_category():
    combined = {
        category: [dict(item) for item in items]
        for category, items in DEFAULT_DEEDS.items()
    }

    for custom in data.get("custom_deeds", []):
        if not isinstance(custom, dict):
            continue
        name = str(custom.get("name", "")).strip()
        category = str(custom.get("category", "")).strip()
        if not name or not category:
            continue
        try:
            suggested_points = max(0, int(custom.get("points", 0)))
        except (TypeError, ValueError, OverflowError):
            suggested_points = 0

        combined.setdefault(category, []).append({
            "name": name,
            "points": suggested_points,
        })

    return combined

def render_progress_dashboard():
    """Show family activity charts, progress goals and encouraging streak info."""
    summary = get_progress_summary()
    total_deeds = len(data.get("deeds", []))

    with st.container(border=True):
        st.subheader("📈 Progress, Goals & Streaks")
        metric_a, metric_b, metric_c, metric_d = st.columns(4)
        metric_a.metric("⭐ Points earned", summary["total_points_earned"])
        metric_b.metric("📅 Active days", summary["active_days"])
        metric_c.metric(
            "🔥 Current streak",
            f'{summary["current_streak"]} day' + ("s" if summary["current_streak"] != 1 else ""),
        )
        metric_d.metric(
            "🗓️ Most active weekday",
            summary["most_consistent_day"],
            help=f'{summary["most_consistent_count"]} deed(s) recorded on that weekday.',
        )

        daily_fraction = min(summary["today_count"] / max(1, summary["daily_goal"]), 1.0)
        weekly_fraction = min(summary["week_count"] / max(1, summary["weekly_goal"]), 1.0)
        st.progress(
            daily_fraction,
            text=f'🎯 Daily goal: {summary["today_count"]} / {summary["daily_goal"]} deeds',
        )
        st.progress(
            weekly_fraction,
            text=f'🌟 Weekly goal: {summary["week_count"]} / {summary["weekly_goal"]} deeds (Monday–Sunday)',
        )

        streak = summary["current_streak"]
        if streak >= 7:
            st.success(f"⚡ Amazing consistency: {streak} days in a row! Keep kindness enjoyable and balanced.")
        elif streak >= 3:
            st.info(f"🔥 Nice momentum: {streak} consecutive days with a good deed.")
        else:
            st.caption("Every day is a fresh start. A streak is a fun bonus—not a requirement.")

        chart_left, chart_right = st.columns(2)
        with chart_left:
            st.markdown("**Good deeds — last 7 days**")
            st.bar_chart(
                {
                    "Day": [day.strftime("%a %d %b") for day in summary["last_7_days"]],
                    "Good deeds": summary["last_7_counts"],
                },
                x="Day",
                y="Good deeds",
            )
        with chart_right:
            st.markdown("**Good deeds — last 30 days**")
            st.line_chart(
                {
                    "Date": [day.strftime("%d %b") for day in summary["last_30_days"]],
                    "Good deeds": summary["last_30_counts"],
                },
                x="Date",
                y="Good deeds",
            )



# =========================================================
# SETTINGS MENU
# =========================================================

def render_settings_menu():

    settings = data["settings"]
    parent_view_active = (
        st.session_state.get("parent_authenticated", False)
        and st.session_state.get("dashboard_mode") == "👨‍👩‍👦 Parent Dashboard"
    )

    st.markdown("### ⚙️ Settings")

    st.caption(
        "Personalise the app. Changes are saved to this family account."
    )

    with st.form("settings_form"):

        st.markdown("#### 🎨 Appearance")

        theme_preset = st.selectbox(
            "Theme",
            list(THEME_PRESETS.keys()),
            index=list(
                THEME_PRESETS.keys()
            ).index(
                settings.get(
                    "theme_preset",
                    "Light",
                )
                if settings.get(
                    "theme_preset",
                    "Light",
                )
                in THEME_PRESETS
                else "Light"
            ),
            key="settings_theme_preset",
        )

        accent_color = st.color_picker(
            "Accent colour",
            valid_hex_color(
                settings.get(
                    "accent_color"
                ),
                "#4F46E5",
            ),
            key="settings_accent_color",
        )

        font_family = st.selectbox(
            "Font",
            list(FONT_FAMILIES.keys()),
            index=list(
                FONT_FAMILIES.keys()
            ).index(
                settings.get(
                    "font_family",
                    "Sans",
                )
                if settings.get(
                    "font_family",
                    "Sans",
                )
                in FONT_FAMILIES
                else "Sans"
            ),
            key="settings_font_family",
        )

        font_scale = st.slider(
            "Text size",
            min_value=85,
            max_value=130,
            value=safe_int(settings.get("font_scale", 100), 100, 85, 130),
            step=5,
            format="%d%%",
            key="settings_font_scale",
        )

        card_radius = st.slider(
            "Rounded corners",
            min_value=0,
            max_value=30,
            value=safe_int(settings.get("card_radius", 15), 15, 0, 30),
            step=1,
            key="settings_card_radius",
        )

        card_shadows = st.toggle(
            "Card shadows",
            value=bool(
                settings.get(
                    "card_shadows",
                    True,
                )
            ),
            key="settings_card_shadows",
        )

        compact_mode = st.toggle(
            "Compact layout",
            value=bool(
                settings.get(
                    "compact_mode",
                    False,
                )
            ),
            key="settings_compact_mode",
        )

        st.markdown(
            "**Custom theme colours**"
        )

        st.caption(
            "These are used when Theme is set to Custom."
        )

        custom_background = st.color_picker(
            "Page background",
            valid_hex_color(
                settings.get(
                    "custom_background"
                ),
                "#FFFFFF",
            ),
            key="settings_custom_background",
        )

        custom_sidebar = st.color_picker(
            "Sidebar background",
            valid_hex_color(
                settings.get(
                    "custom_sidebar"
                ),
                "#F8FAFC",
            ),
            key="settings_custom_sidebar",
        )

        custom_card = st.color_picker(
            "Card background",
            valid_hex_color(
                settings.get(
                    "custom_card"
                ),
                "#F3F4F6",
            ),
            key="settings_custom_card",
        )

        custom_text = st.color_picker(
            "Text colour",
            valid_hex_color(
                settings.get(
                    "custom_text"
                ),
                "#1F2937",
            ),
            key="settings_custom_text",
        )

        st.divider()

        st.markdown("#### 🌱 Motivation & rewards")
        motivation_modes = [
            "Growth first",
            "Extra effort only",
            "Points for every deed",
            "No points",
        ]

        if parent_view_active:
            current_motivation_mode = settings.get(
                "motivation_mode", "Growth first"
            )
            if current_motivation_mode not in motivation_modes:
                current_motivation_mode = "Growth first"
            motivation_mode = st.selectbox(
                "How should the app handle points?",
                motivation_modes,
                index=motivation_modes.index(current_motivation_mode),
                help=(
                    "Growth first records deeds without points. Extra effort only "
                    "awards points when a parent marks a deed as voluntary extra effort. "
                    "Points for every deed keeps the traditional system. No points "
                    "turns off point earning and the rewards shop."
                ),
                key="settings_motivation_mode",
            )
            mode_descriptions = {
                "Growth first": "Deeds are recorded and appreciated, without points attached.",
                "Extra effort only": "Points are reserved for deeds a parent identifies as voluntary extra effort.",
                "Points for every deed": "Each recorded deed earns its suggested points.",
                "No points": "The app tracks deeds, reflections and appreciation without point rewards.",
            }
            st.caption(mode_descriptions[motivation_mode])
        else:
            motivation_mode = settings.get("motivation_mode", "Growth first")
            st.caption("A parent or guardian can change the motivation mode from Parent Dashboard settings.")

        st.divider()
        st.markdown("#### 🧩 Dashboard")

        show_motivation = st.toggle(
            "Show motivational message",
            value=bool(
                settings.get(
                    "show_motivation",
                    True,
                )
            ),
            key="settings_show_motivation",
        )

        show_progress = st.toggle(
            "Show level progress",
            value=bool(
                settings.get(
                    "show_progress",
                    True,
                )
            ),
            key="settings_show_progress",
        )

        show_badges = st.toggle(
            "Show badges",
            value=bool(
                settings.get(
                    "show_badges",
                    True,
                )
            ),
            key="settings_show_badges",
        )

        show_recent_deeds = st.toggle(
            "Show recent good deeds",
            value=bool(
                settings.get(
                    "show_recent_deeds",
                    True,
                )
            ),
            key="settings_show_recent_deeds",
        )

        recent_deeds_count = st.slider(
            "Recent deeds to show",
            min_value=3,
            max_value=15,
            value=safe_int(settings.get("recent_deeds_count", 8), 8, 3, 15),
            step=1,
            key="settings_recent_deeds_count",
        )

        show_rewards = st.toggle(
            "Show rewards shop",
            value=bool(
                settings.get(
                    "show_rewards",
                    True,
                )
            ),
            key="settings_show_rewards",
        )

        st.markdown("#### 🎯 Daily & weekly goals")
        if parent_view_active:
            daily_goal_target = st.number_input(
                "Daily good-deed goal",
                min_value=1,
                max_value=20,
                value=safe_int(settings.get("daily_goal_target", 3), 3, 1, 20),
                step=1,
                key="settings_daily_goal_target",
                help="A friendly target; missing a day is not a punishment.",
            )
            weekly_goal_target = st.number_input(
                "Weekly good-deed goal",
                min_value=1,
                max_value=100,
                value=safe_int(settings.get("weekly_goal_target", 10), 10, 1, 100),
                step=1,
                key="settings_weekly_goal_target",
                help="Counts deeds recorded Monday through Sunday.",
            )
        else:
            daily_goal_target = safe_int(settings.get("daily_goal_target", 3), 3, 1, 20)
            weekly_goal_target = safe_int(settings.get("weekly_goal_target", 10), 10, 1, 100)
            st.caption("Daily and weekly targets are managed by a parent in Parent Dashboard settings.")

        st.divider()

        st.markdown("#### ♿ Accessibility")

        high_contrast = st.toggle(
            "High contrast",
            value=bool(
                settings.get(
                    "high_contrast",
                    False,
                )
            ),
            key="settings_high_contrast",
        )

        large_controls = st.toggle(
            "Larger buttons and inputs",
            value=bool(
                settings.get(
                    "large_controls",
                    False,
                )
            ),
            key="settings_large_controls",
        )

        reduce_motion = st.toggle(
            "Reduce motion",
            value=bool(
                settings.get(
                    "reduce_motion",
                    False,
                )
            ),
            key="settings_reduce_motion",
        )

        st.divider()

        st.markdown("#### 🔐 Privacy")

        show_account_identifier = st.toggle(
            "Show signed-in email / phone in sidebar",
            value=bool(
                settings.get(
                    "show_account_identifier",
                    True,
                )
            ),
            key="settings_show_account_identifier",
        )

        timeout_options = [5, 10, 15, 30]
        current_timeout = safe_int(settings.get("parent_lock_timeout_minutes", 10), 10, 5, 30)
        if current_timeout not in timeout_options:
            current_timeout = 10
        if parent_view_active:
            parent_lock_timeout_minutes = st.selectbox(
                "Parent Dashboard auto-lock after inactivity",
                timeout_options,
                index=timeout_options.index(current_timeout),
                format_func=lambda minutes: f"{minutes} minutes",
                key="settings_parent_lock_timeout_minutes",
                help="The dashboard locks the next time the app is used after this idle period.",
            )
        else:
            parent_lock_timeout_minutes = current_timeout
            st.caption(f"Parent Dashboard auto-lock: {current_timeout} minutes of inactivity (parent-managed).")

        if parent_view_active:

            st.divider()

            st.markdown(
                "#### 👨‍👩‍👦 Parent profile"
            )

            updated_child_name = st.text_input(
                "Child's display name",
                value=data.get(
                    "child_name",
                    "",
                ),
                key="settings_child_display_name",
            )

        else:

            updated_child_name = data.get(
                "child_name",
                "",
            )

        apply_button = st.form_submit_button(
            "💾 Save Settings",
            type="primary",
            use_container_width=True,
        )

        if apply_button:

            data["settings"] = {
                "theme_preset": theme_preset,
                "accent_color": accent_color,
                "custom_background": custom_background,
                "custom_sidebar": custom_sidebar,
                "custom_card": custom_card,
                "custom_text": custom_text,
                "font_family": font_family,
                "font_scale": font_scale,
                "card_radius": card_radius,
                "card_shadows": card_shadows,
                "compact_mode": compact_mode,
                "high_contrast": high_contrast,
                "reduce_motion": reduce_motion,
                "large_controls": large_controls,
                "show_progress": show_progress,
                "show_badges": show_badges,
                "show_recent_deeds": show_recent_deeds,
                "show_rewards": show_rewards,
                "show_motivation": show_motivation,
                "motivation_mode": motivation_mode,
                "recent_deeds_count": recent_deeds_count,
                "show_account_identifier": show_account_identifier,
                "daily_goal_target": int(daily_goal_target),
                "weekly_goal_target": int(weekly_goal_target),
                "parent_lock_timeout_minutes": int(parent_lock_timeout_minutes),
            }

            if (
                st.session_state.get(
                    "parent_authenticated",
                    False,
                )
                and updated_child_name.strip()
            ):
                data["child_name"] = (
                    updated_child_name.strip()
                )

            save_data(data)

            st.rerun()

    st.divider()

    st.markdown("#### 📦 Data & account")

    safe_export = {
        "child_name": data.get(
            "child_name",
            "",
        ),
        "points": data.get(
            "points",
            0,
        ),
        "deeds": data.get(
            "deeds",
            [],
        ),
        "redemptions": data.get(
            "redemptions",
            [],
        ),
        "pending_redemptions": data.get("pending_redemptions", []),
        "reward_request_history": data.get("reward_request_history", []),
        "pending_deeds": data.get("pending_deeds", []),
        "child_deed_request_history": data.get("child_deed_request_history", []),
        "custom_deeds": data.get(
            "custom_deeds",
            [],
        ),
        "reflections": data.get("reflections", []),
        "appreciations": data.get("appreciations", []),
        "rewards": data.get(
            "rewards",
            [],
        ),
        "settings": data.get(
            "settings",
            {},
        ),
    }

    if parent_view_active:
        st.download_button(
            "⬇️ Export family data",
            data=json.dumps(
                safe_export,
                indent=4,
                ensure_ascii=False,
            ),
            file_name="good_deeds_backup.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.caption("Unlock and select Parent Dashboard to export family data.")

    if st.button(
        "↩️ Reset appearance & dashboard settings",
        use_container_width=True,
    ):

        current_motivation_mode = data.get("settings", {}).get(
            "motivation_mode", "Growth first"
        )
        data["settings"] = copy.deepcopy(DEFAULT_SETTINGS)
        data["settings"]["motivation_mode"] = current_motivation_mode
        st.session_state["_reset_settings_widgets_pending"] = True

        save_data(data)

        st.rerun()

    if parent_view_active:
        if st.button(
            "🧭 Replay Parent Welcome Tour",
            use_container_width=True,
            help="Show the first-time guide again.",
        ):
            data["parent_tour_completed"] = False
            st.session_state["parent_tour_step"] = 0
            save_data(data)
            st.rerun()

    if st.button(
        "🚪 Log Out",
        use_container_width=True,
    ):

        st.session_state.logged_in = False
        st.session_state.parent_authenticated = False
        st.session_state.parent_last_activity = 0.0
        st.session_state.auth_stage = "identifier"
        st.session_state.active_identifier = ""
        st.session_state.data = copy.deepcopy(DEFAULT_DATA)
        st.session_state["dashboard_mode"] = "👦 Child Dashboard"

        clear_otp()

        st.rerun()

    st.caption(
        "Good Deeds • Settings v1"
    )

# =========================================================
# PARENT FIRST-LOGIN INTRODUCTION
# =========================================================

PARENT_TOUR_STEPS = [
    {
        "title": "1. Your Parent Dashboard",
        "body": "This is the family control centre. Record a deed, add an encouraging note, read your child's optional reflections, and review the history. The Parent Dashboard stays protected by its separate password.",
        "bullets": [
            "Use the dashboard selector in the left sidebar to switch between Child and Parent views.",
            "A child can submit a deed for parent review; it is recorded only after approval.",
            "Appreciation notes are private encouragement and never award points.",
        ],
    },
    {
        "title": "2. Choose your family's motivation approach",
        "body": "Open the ⚙️ menu at the top-right and find Motivation & rewards in Settings. The default is Growth first, so new deeds are recorded without automatically earning points.",
        "bullets": [
            "Growth first: deeds are recorded without points; the rewards shop is hidden.",
            "Extra effort only: points are awarded only when a parent explicitly marks a deed as voluntary extra effort.",
            "Points for every deed: keeps the traditional points system.",
            "No points: tracks deeds, reflections and appreciation without point rewards.",
        ],
    },
    {
        "title": "3. Personalise appearance",
        "body": "The ⚙️ menu opens Settings. Changes take effect after you select Save Settings.",
        "bullets": [
            "Choose Light, Dark, Warm, Cool or Custom themes, including custom page, sidebar, card and text colours.",
            "Change the font, text size, rounded corners, card shadows and compact layout.",
            "Use Dashboard options to show or hide motivational messages, progress, badges, recent deeds and the rewards shop.",
        ],
    },
    {
        "title": "4. Accessibility options",
        "body": "These settings are designed to make the app easier to read and operate. You can return to them whenever you need.",
        "bullets": [
            "High contrast: switches to a high-contrast colour palette.",
            "Larger buttons and inputs: makes controls taller and easier to select.",
            "Reduce motion: reduces interface animations and transitions.",
            "Text size and font choices are also useful readability adjustments.",
        ],
    },
    {
        "title": "5. Privacy, backup and getting help",
        "body": "Each family account is stored separately in the app database. Streamlit Cloud local files are not a permanent backup, so use Export family data regularly and keep the backup safe.",
        "bullets": [
            "Use the privacy toggle to hide or show the signed-in email/phone in the sidebar.",
            "Export family data creates a JSON backup including deeds, rewards, approval requests and histories, reflections, appreciation notes and settings; it excludes passwords and account credentials.",
            "Use Replay Parent Welcome Tour in Settings to see this guide again.",
            "Use the sidebar Lock Parent Dashboard button when stepping away; inactivity also triggers an automatic lock.",
        ],
    },
]


def render_parent_intro_tour():
    """Show a persistent, parent-only guided introduction until completed."""
    if data.get("parent_tour_completed", False):
        return

    step_index = safe_int(
        st.session_state.get("parent_tour_step", 0),
        0,
        0,
        len(PARENT_TOUR_STEPS) - 1,
    )
    step = PARENT_TOUR_STEPS[step_index]

    with st.container(border=True):
        st.markdown("## 👋 Welcome to Good Deeds — Parent quick tour")
        st.caption("You will see this guide once. You can replay it later from the ⚙️ gear in the app header.")
        st.progress(
            (step_index + 1) / len(PARENT_TOUR_STEPS),
            text=f"Step {step_index + 1} of {len(PARENT_TOUR_STEPS)}",
        )
        st.subheader(step["title"])
        st.markdown(
            f'<div class="gd-tour-text">{html.escape(step["body"])}</div>',
            unsafe_allow_html=True,
        )
        tour_bullets = "".join(
            f'<li>{html.escape(str(bullet))}</li>' for bullet in step["bullets"]
        )
        st.markdown(
            f'<div class="gd-tour-text gd-tour-bullets"><ul>{tour_bullets}</ul></div>',
            unsafe_allow_html=True,
        )

        previous_col, next_col, skip_col = st.columns([1, 1.2, 1])
        with previous_col:
            if st.button(
                "← Previous",
                disabled=(step_index == 0),
                key=f"parent_tour_previous_{step_index}",
                use_container_width=True,
            ):
                st.session_state["parent_tour_step"] = max(0, step_index - 1)
                st.rerun()

        with next_col:
            is_last_step = step_index == len(PARENT_TOUR_STEPS) - 1
            next_label = "Finish tour ✓" if is_last_step else "Next →"
            if st.button(
                next_label,
                type="primary",
                key=f"parent_tour_next_{step_index}",
                use_container_width=True,
            ):
                if is_last_step:
                    data["parent_tour_completed"] = True
                    save_data(data)
                    st.session_state.pop("parent_tour_step", None)
                else:
                    st.session_state["parent_tour_step"] = step_index + 1
                st.rerun()

        with skip_col:
            if st.button(
                "Skip",
                key=f"parent_tour_skip_{step_index}",
                use_container_width=True,
            ):
                data["parent_tour_completed"] = True
                save_data(data)
                st.session_state.pop("parent_tour_step", None)
                st.rerun()


# =========================================================
# APP HEADER AND SETTINGS MENU
# =========================================================

header_title_col, header_menu_col = st.columns([12, 1])
with header_title_col:
    st.markdown("### ⭐ Good Deeds")
with header_menu_col:
    with st.popover("⚙️", help="Settings, appearance, accessibility and data tools"):

        render_settings_menu()

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown("## ⭐ Good Deeds")
st.sidebar.caption("Building good habits, one deed at a time.")

settings = data["settings"]

account_identifier = data.get(
    "account",
    {},
).get(
    "identifier",
    "",
)

if settings.get(
    "show_account_identifier",
    True,
):
    st.sidebar.caption(
        f"Signed in as: {account_identifier}"
    )

def lock_parent_dashboard():
    """Lock parent-only access and switch back to the child dashboard."""
    st.session_state.parent_authenticated = False
    st.session_state.parent_last_activity = 0.0
    st.session_state["dashboard_mode"] = "👦 Child Dashboard"


# Apply a dashboard switch requested by the timeout check on the prior run,
# before Streamlit instantiates the dashboard radio widget.
if st.session_state.pop("_force_child_dashboard", False):
    st.session_state["dashboard_mode"] = "👦 Child Dashboard"

mode = st.sidebar.radio(
    "Choose Dashboard",
    [
        "👦 Child Dashboard",
        "👨‍👩‍👦 Parent Dashboard",
    ],
    key="dashboard_mode",
)

# Selecting the child view ends the parent-authenticated session so the child
# cannot switch back into parent controls without entering the password again.
if mode == "👦 Child Dashboard" and st.session_state.parent_authenticated:
    st.session_state.parent_authenticated = False
    st.session_state.parent_last_activity = 0.0
    st.sidebar.caption("🔒 Parent access locked when switching to Child Dashboard.")

# Parent access expires after the configured idle interval. Streamlit checks
# this on the next app interaction/rerun, then returns to the child dashboard.
if mode == "👨‍👩‍👦 Parent Dashboard" and st.session_state.parent_authenticated:
    timeout_minutes = safe_int(
        data.get("settings", {}).get("parent_lock_timeout_minutes", 10),
        10,
        5,
        30,
    )
    last_activity = float(st.session_state.get("parent_last_activity", 0.0) or 0.0)
    if last_activity and (time.time() - last_activity) >= timeout_minutes * 60:
        st.session_state.parent_authenticated = False
        st.session_state.parent_last_activity = 0.0
        st.session_state["_force_child_dashboard"] = True
        st.session_state["_parent_timeout_notice"] = True
        st.rerun()
    else:
        st.session_state.parent_last_activity = time.time()

if st.session_state.pop("_parent_timeout_notice", False):
    st.sidebar.warning("🔒 Parent Dashboard locked after inactivity.")

st.sidebar.divider()

if mode == "👨‍👩‍👦 Parent Dashboard":

    if not st.session_state.parent_authenticated:

        st.sidebar.subheader(
            "🔒 Parent Access"
        )

        entered_parent_password = st.sidebar.text_input(
            "Enter Parent Dashboard Password",
            type="password",
        )

        if st.sidebar.button(
            "🔓 Unlock Parent Dashboard"
        ):

            if check_parent_password(
                entered_parent_password
            ):

                st.session_state.parent_authenticated = True
                st.session_state.parent_last_activity = time.time()

                st.rerun()

            else:

                st.sidebar.error(
                    "❌ Incorrect Parent Dashboard password."
                )

    else:

        st.sidebar.success(
            "✅ Parent access unlocked."
        )

        st.sidebar.button(
            "🔒 Lock Parent Dashboard",
            use_container_width=True,
            help="Lock parent-only access and return to the Child Dashboard.",
            on_click=lock_parent_dashboard,
        )

if mode == "👨‍👩‍👦 Parent Dashboard" and st.session_state.parent_authenticated:
    pending_approval_count = (
        len(data.get("pending_deeds", []))
        + len(data.get("pending_redemptions", []))
    )
    if pending_approval_count:
        st.sidebar.warning(f"🔔 {pending_approval_count} approval(s) waiting")
    else:
        st.sidebar.caption("🔔 No pending approvals")

# =========================================================
# BLOCK PARENT ACCESS
# =========================================================

if (
    mode == "👨‍👩‍👦 Parent Dashboard"
    and not st.session_state.parent_authenticated
):

    st.title(
        "🔒 Parent Dashboard Locked"
    )

    st.write(
        "This area is only accessible to a parent or guardian."
    )

    st.markdown(
        '<div class="gd-locked-message">Enter the Parent Dashboard password in the sidebar to continue.</div>',
        unsafe_allow_html=True,
    )

    st.stop()

# =========================================================
# CHILD DASHBOARD
# =========================================================

if mode == "👦 Child Dashboard":

    settings = data["settings"]

    motivation_mode = settings.get("motivation_mode", "Growth first")
    growth_first_mode = motivation_mode in ("Growth first", "No points")
    level_name = get_level(data.get("points", 0))

    st.title(f"👋 Welcome, {data['child_name']}!")
    st.subheader("Your Good Deeds Dashboard")

    if settings.get("show_motivation", True):
        if growth_first_mode:
            motivation = (
                "Kindness matters even when nobody gives points. "
                "Notice how your choices help people around you. 💛"
            )
        elif data.get("points", 0) < 100:
            motivation = "Small helpful choices can make a real difference. ⭐"
        elif data.get("points", 0) < 600:
            motivation = "Keep noticing opportunities to be kind and responsible. 🌱"
        else:
            motivation = "Your choices show care, effort and responsibility. 🌟"

        st.markdown(
            f'<div class="gd-motivation">{motivation}</div>',
            unsafe_allow_html=True,
        )

    if growth_first_mode:
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Good Deeds Recorded", len(data.get("deeds", [])))
        col2.metric("🪞 Reflections", len(data.get("reflections", [])))
        col3.metric("💛 Appreciation Notes", len(data.get("appreciations", [])))
        if data.get("points", 0) > 0:
            st.caption(
                "Your family’s existing point balance has been preserved. "
                "Growth first mode does not award points for newly recorded deeds. "
                "A parent can change this in Settings."
            )
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("⭐ Current Points", data.get("points", 0))
        col2.metric("✅ Good Deeds", len(data.get("deeds", [])))
        col3.metric("🏆 Level", level_name)
        col4.metric("🎁 Rewards Claimed", len(data.get("redemptions", [])))

        if settings.get("show_progress", True):
            st.divider()
            st.subheader("📈 Your Progress")

            point_total = safe_int(data.get("points", 0), 0, 0, 10_000_000)
            thresholds = [100, 300, 600, 1000, 2000]
            lower_bound = 0
            next_level = None
            for threshold in thresholds:
                if point_total < threshold:
                    next_level = threshold
                    break
                lower_bound = threshold

            if next_level is not None:
                progress_fraction = (point_total - lower_bound) / max(1, next_level - lower_bound)
                st.progress(max(0.0, min(progress_fraction, 1.0)))
                st.write(
                    f"🎯 **{next_level - point_total} more points** until your next level."
                )
            else:
                st.progress(1.0)
                st.write("💎 You have reached the highest level!")

    if settings.get("show_progress", True):
        render_progress_dashboard()

    if settings.get(
        "show_badges",
        True,
    ):

        st.subheader(
            "🏅 Your Badges"
        )

        badges = get_badges()

        if badges:
            # Keep badge cards in short rows so they remain readable on phones.
            for start in range(0, len(badges), 3):
                badge_batch = badges[start:start + 3]
                badge_cols = st.columns(len(badge_batch))
                for offset, badge in enumerate(badge_batch):
                    with badge_cols[offset]:
                        st.markdown(
                            f"""
                            <div class="badge-card">
                                <div style="font-size:35px;">{badge[0]}</div>
                                <b>{badge[1]}</b>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        else:

            st.info(
                "Complete your first good deed "
                "to unlock a badge! 🌱"
            )

    if settings.get(
        "show_recent_deeds",
        True,
    ):

        st.divider()

        st.subheader(
            "✅ Recent Good Deeds"
        )

        recent_count = safe_int(
            settings.get("recent_deeds_count", 8), 8, 3, 15
        )

        if data["deeds"]:

            for deed in data["deeds"][:recent_count]:
                earned_points = safe_int(deed.get("points", 0), 0, 0, 1_000_000)
                points_label = (
                    f"+{earned_points} bonus points"
                    if earned_points > 0
                    else "Recorded without points"
                )
                deed_name_html = html.escape(str(deed.get("name", "Good deed")))
                deed_category_html = html.escape(str(deed.get("category", "")))
                deed_date_html = html.escape(str(deed.get("date", "")))
                deed_description_html = html.escape(str(deed.get("description", "")))
                st.markdown(
                    f"""
                    <div class="deed-card">
                        <b>{deed_name_html}</b><br>
                        <small>{deed_category_html} • {deed_date_html}</small><br>
                        {deed_description_html}<br><br>
                        <strong>{points_label}</strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        else:

            st.info(
                "No good deeds recorded yet."
            )

    st.divider()
    st.subheader("📝 Share a Good Deed")
    st.caption("Tell your parent about a deed you did. It will be reviewed before it is added to your history or earns any points.")

    available_deeds_by_category = get_all_deeds_by_category()
    submission_categories = list(available_deeds_by_category.keys())
    submission_category = st.selectbox(
        "Category",
        submission_categories,
        key="child_submission_category",
    )
    submission_deeds = available_deeds_by_category[submission_category]
    with st.form("child_deed_submission_form", clear_on_submit=True):
        submission_labels = [
            f'{item["name"]} · {item["points"]} ⭐'
            for item in submission_deeds
        ]
        selected_submission_label = st.selectbox(
            "Good deed",
            submission_labels,
            key=f"child_submission_deed_label_{submission_category}",
        )
        selected_submission_index = submission_labels.index(selected_submission_label)
        selected_submission_deed = submission_deeds[selected_submission_index]
        submission_description = st.text_area(
            "Optional details",
            max_chars=500,
            placeholder="What did you do? Keep it brief and honest.",
            key="child_submission_description",
        )
        submit_deed_request = st.form_submit_button("📨 Send to Parent for Review")

    if submit_deed_request:
        submit_child_deed(
            selected_submission_deed["name"],
            submission_category,
            selected_submission_deed["points"],
            submission_description,
        )
        st.success("Your good deed was sent to your parent for review. No points were added yet.")
        st.rerun()

    with st.expander("📬 My deed submissions"):
        pending_child_submissions = data.get("pending_deeds", [])
        reviewed_child_submissions = data.get("child_deed_request_history", [])
        if pending_child_submissions:
            st.markdown("**Waiting for parent review**")
            for request in pending_child_submissions[:10]:
                st.write(f'⏳ **{request.get("name", "Good deed")}** — {request.get("category", "")}')
                st.caption(f'Submitted: {request.get("submitted_at", "")}')
        if reviewed_child_submissions:
            st.markdown("**Reviewed**")
            for request in reviewed_child_submissions[:10]:
                status = request.get("status", "Reviewed")
                st.write(f'{"✅" if status == "Approved" else "📝"} **{request.get("name", "Good deed")}** — {status}')
                if request.get("review_note"):
                    st.caption("Parent note: " + request["review_note"])
                st.caption(request.get("reviewed_at", ""))
        if not pending_child_submissions and not reviewed_child_submissions:
            st.caption("You haven't sent any deeds for review yet.")

    st.divider()
    st.subheader("🌱 Reflection Corner")
    st.caption("Reflecting is optional. There are no points for your answers.")

    with st.expander("Think about something you did this week"):
        with st.form("child_reflection_form", clear_on_submit=True):
            reflection_helped = st.text_area(
                "What did you do that helped someone?",
                max_chars=1000,
            )
            reflection_impact = st.text_area(
                "What did you notice about how it affected them?",
                max_chars=1000,
            )
            reflection_goal = st.text_input(
                "Something you might try next week (optional)",
                max_chars=300,
            )
            save_reflection = st.form_submit_button("Save Reflection")

        if save_reflection:
            if not (reflection_helped.strip() or reflection_impact.strip() or reflection_goal.strip()):
                st.info("Write a little reflection before saving, or leave it for another time.")
            else:
                data.setdefault("reflections", []).insert(0, {
                    "helped": reflection_helped.strip(),
                    "noticed": reflection_impact.strip(),
                    "next_goal": reflection_goal.strip(),
                    "date": now_local().strftime("%d %b %Y, %I:%M %p"),
                })
                save_data(data)
                st.success("Reflection saved. No points were added.")
                st.rerun()

    if data.get("reflections"):
        with st.expander("My previous reflections"):
            for reflection in data["reflections"][:5]:
                st.markdown(f"**{reflection.get('date', '')}**")
                if reflection.get("helped"):
                    st.write("**What I did:** " + reflection["helped"])
                if reflection.get("noticed"):
                    st.write("**What I noticed:** " + reflection["noticed"])
                if reflection.get("next_goal"):
                    st.write("**Next time:** " + reflection["next_goal"])
                st.divider()

    with st.expander("💛 Appreciation from your parent"):
        appreciations = data.get("appreciations", [])
        if appreciations:
            for item in appreciations[:5]:
                st.markdown(f"**{item.get('date', '')}**")
                st.write(item.get("note", ""))
                st.divider()
        else:
            st.caption("When your parent notices something thoughtful, their appreciation notes will appear here. No points are attached.")

    if settings.get("show_rewards", True) and motivation_mode not in ("Growth first", "No points"):

        st.divider()
        st.subheader("🎁 Rewards Shop")

        pending_reward_points = sum(
            safe_int(item.get("cost", 0), 0, 0, 1_000_000)
            for item in data.get("pending_redemptions", [])
        )
        current_reward_points = safe_int(data.get("points", 0), 0, 0, 10_000_000)
        available_reward_points = max(0, current_reward_points - pending_reward_points)
        st.caption(
            f'Balance: {current_reward_points} ⭐ • Reserved for pending requests: '
            f'{pending_reward_points} ⭐ • Available: {available_reward_points} ⭐'
        )

        for start in range(0, len(data["rewards"]), 3):
            reward_cols = st.columns(3)
            for offset, reward in enumerate(data["rewards"][start:start + 3]):
                i = start + offset
                with reward_cols[offset]:
                    reward_name = html.escape(str(reward.get("name", "Reward")))
                    reward_emoji = html.escape(str(reward.get("emoji", "🎁")))
                    reward_cost = safe_int(reward.get("cost", 0), 0, 0, 1_000_000)
                    st.markdown(
                        f"""
                        <div class="reward-card">
                            <div class="reward-emoji">{reward_emoji}</div>
                            <div class="reward-name">{reward_name}</div>
                            <div class="reward-cost">{reward_cost} ⭐</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        f"Request reward · {reward_cost} ⭐",
                        key=f"reward_{i}",
                        disabled=(available_reward_points < reward_cost),
                        use_container_width=True,
                    ):
                        if redeem_reward(reward):
                            st.success(
                                f'Request sent for {reward.get("name", "Reward")}. '
                                "A parent must approve it; points are deducted only after approval."
                            )
                            st.rerun()
                        else:
                            st.info("You don't have enough available points for this request yet.")

        with st.expander("📬 My reward requests"):
            pending_reward_requests = data.get("pending_redemptions", [])
            reviewed_reward_requests = data.get("reward_request_history", [])
            if pending_reward_requests:
                st.markdown("**Waiting for parent approval**")
                for request in pending_reward_requests[:10]:
                    st.write(f'⏳ **{request.get("reward", "Reward")}** — {request.get("cost", 0)} ⭐')
                    st.caption(f'Requested: {request.get("requested_at", "")}')
            if reviewed_reward_requests:
                st.markdown("**Reviewed**")
                for request in reviewed_reward_requests[:10]:
                    st.write(f'**{request.get("reward", "Reward")}** — {request.get("status", "Reviewed")}')
                    if request.get("review_note"):
                        st.caption("Parent note: " + request["review_note"])
                    st.caption(request.get("reviewed_at", ""))
            if not pending_reward_requests and not reviewed_reward_requests:
                st.caption("You haven't requested a reward yet.")

# =========================================================
# PARENT DASHBOARD
# =========================================================

else:

    st.title(
        "👨‍👩‍👦 Parent Dashboard 🔓"
    )

    st.subheader(
        f"Managing {data['child_name']}'s Good Deeds"
    )

    render_parent_intro_tour()

    parent_dashboard_tabs = st.tabs(
        [
            "🏠 Overview",
            "🔔 Approvals",
            "⭐ Record Deeds",
            "💛 Notes & Reflections",
            "🎁 Rewards",
            "📚 Deeds & History",
            "⚙️ Parent Settings",
        ]
    )
    overview_tab, approvals_tab, record_deeds_tab, notes_tab, rewards_tab, deeds_history_tab, parent_settings_tab = parent_dashboard_tabs

    with overview_tab:
        st.caption("At-a-glance family progress and activity.")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "⭐ Current Points",
            data["points"],
        )

        col2.metric(
            "✅ Total Good Deeds",
            len(data["deeds"]),
        )

        col3.metric(
            "🎁 Rewards Claimed",
            len(data["redemptions"]),
        )

        render_progress_dashboard()

        st.divider()


    with approvals_tab:
        st.caption("Review child-submitted deeds and reward requests. Approvals are handled here.")
        pending_child_deed_requests = data.get("pending_deeds", [])
        pending_reward_requests = data.get("pending_redemptions", [])
        total_pending_approvals = len(pending_child_deed_requests) + len(pending_reward_requests)

        with st.container(border=True):
            st.subheader("🔔 Parent Notifications")
            notify_deeds, notify_rewards, notify_total = st.columns(3)
            notify_deeds.metric("📝 Deeds awaiting review", len(pending_child_deed_requests))
            notify_rewards.metric("🎁 Reward requests", len(pending_reward_requests))
            notify_total.metric("📬 Total pending", total_pending_approvals)
            if total_pending_approvals == 0:
                st.caption("You're all caught up—no approvals are waiting.")
            else:
                st.info("Review the requests below. Points are awarded for a submitted deed only after approval, and reward points are deducted only after reward approval.")

        if pending_child_deed_requests:
            st.subheader("📨 Child Good-Deed Submissions")
            for request in pending_child_deed_requests:
                request_id = str(request.get("request_id", ""))
                with st.container(border=True):
                    st.markdown(f'**{request.get("name", "Good deed")}** · {request.get("category", "")}')
                    st.caption(f'Submitted: {request.get("submitted_at", "")} · Suggested points: {request.get("suggested_points", 0)} ⭐')
                    if request.get("description"):
                        st.write(request["description"])

                    extra_effort_approval = False
                    if data.get("settings", {}).get("motivation_mode", "Growth first") == "Extra effort only":
                        extra_effort_approval = st.checkbox(
                            "This submission qualifies as voluntary extra effort",
                            key=f"approve_child_deed_extra_{request_id}",
                        )

                    rejection_note = st.text_input(
                        "Optional note if not approved",
                        key=f"reject_child_deed_note_{request_id}",
                        placeholder="e.g. Please tell me a little more about it",
                    )
                    approve_col, reject_col = st.columns(2)
                    with approve_col:
                        if st.button("✅ Approve deed", key=f"approve_child_deed_{request_id}", use_container_width=True):
                            approved, awarded_points = approve_child_deed(
                                request_id,
                                is_extra_effort=extra_effort_approval,
                            )
                            if approved:
                                if awarded_points:
                                    st.success(f'Deed approved and {awarded_points} ⭐ awarded.')
                                else:
                                    st.success("Deed approved and recorded. No points were attached under the current motivation settings.")
                                st.rerun()
                            else:
                                st.error("This submission could not be found. Refresh and try again.")
                    with reject_col:
                        if st.button("📝 Not approved", key=f"reject_child_deed_{request_id}", use_container_width=True):
                            if reject_child_deed(request_id, rejection_note):
                                st.success("Submission reviewed. The child can see your note in their submissions.")
                                st.rerun()
                            else:
                                st.error("This submission could not be found. Refresh and try again.")

        if pending_reward_requests:
            st.subheader("🎁 Reward Requests to Approve")
            for request in pending_reward_requests:
                request_id = str(request.get("request_id", ""))
                with st.container(border=True):
                    st.markdown(f'**{request.get("reward", "Reward")}** — {request.get("cost", 0)} ⭐')
                    st.caption(f'Requested: {request.get("requested_at", "")}')
                    rejection_note = st.text_input(
                        "Optional note if not approved",
                        key=f"reject_reward_note_{request_id}",
                        placeholder="Optional explanation for the child",
                    )
                    approve_col, reject_col = st.columns(2)
                    with approve_col:
                        if st.button("✅ Approve reward", key=f"approve_reward_{request_id}", use_container_width=True):
                            approved, message = approve_reward_request(request_id)
                            if approved:
                                st.success(f'Reward approved. {request.get("cost", 0)} ⭐ deducted.')
                                st.rerun()
                            else:
                                st.error(message)
                    with reject_col:
                        if st.button("📝 Not approved", key=f"reject_reward_{request_id}", use_container_width=True):
                            if reject_reward_request(request_id, rejection_note):
                                st.success("Reward request reviewed. The child can see your note.")
                                st.rerun()
                            else:
                                st.error("This request could not be found. Refresh and try again.")



    with notes_tab:
        st.caption("Encourage your child and review their optional reflections.")
        st.subheader("💛 Appreciate without points")
        st.caption("Use specific appreciation to show what you noticed; this never changes the points balance.")

        with st.form("parent_appreciation_form", clear_on_submit=True):
            appreciation_note = st.text_area(
                "What did you notice your child doing well?",
                placeholder="Example: I noticed you made room for your sibling and listened patiently.",
                max_chars=1000,
            )
            save_appreciation = st.form_submit_button("Save Appreciation Note")

        if save_appreciation:
            if not appreciation_note.strip():
                st.warning("Write a short appreciation note first.")
            else:
                data.setdefault("appreciations", []).insert(0, {
                    "note": appreciation_note.strip(),
                    "date": now_local().strftime("%d %b %Y, %I:%M %p"),
                })
                save_data(data)
                st.success("Appreciation saved. No points were awarded.")
                st.rerun()

        st.subheader("🌱 Child reflections")
        reflections = data.get("reflections", [])
        if reflections:
            for reflection in reflections[:10]:
                st.markdown(f"**{reflection.get('date', '')}**")
                if reflection.get("helped"):
                    st.write("**What they did:** " + reflection["helped"])
                if reflection.get("noticed"):
                    st.write("**What they noticed:** " + reflection["noticed"])
                if reflection.get("next_goal"):
                    st.write("**Next time:** " + reflection["next_goal"])
                st.divider()
        else:
            st.caption("No reflections saved yet. Reflection is optional and should not be used as a score.")

        st.divider()



    with record_deeds_tab:
        st.caption("Record a good deed from the library or create a custom deed.")
        st.subheader(
            "⭐ Record a Good Deed"
        )

        record_deed_mode = st.radio(
            "What would you like to do?",
            [
                "📋 Choose from Good Deeds List",
                "➕ Add / Award a Custom Good Deed",
            ],
            horizontal=True,
            key="parent_record_deed_mode",
        )

        if record_deed_mode == "📋 Choose from Good Deeds List":

            all_deeds = get_all_deeds_by_category()

            categories = list(
                all_deeds.keys()
            )

            selected_category = st.selectbox(
                "Choose a category",
                categories,
                key="preset_category",
            )

            deeds_in_category = all_deeds[
                selected_category
            ]

            deed_names = [
                f"{item['name']}  •  {item['points']} ⭐"
                for item in deeds_in_category
            ]

            selected_deed_label = st.selectbox(
                "Choose a good deed",
                deed_names,
                key="preset_deed",
            )

            selected_index = deed_names.index(
                selected_deed_label
            )

            selected_deed = deeds_in_category[
                selected_index
            ]

            motivation_mode = data.get("settings", {}).get("motivation_mode", "Growth first")
            is_extra_effort = False
            preset_extra_effort_epoch = st.session_state.get("preset_extra_effort_epoch", 0)
            preset_extra_effort_key = f"preset_extra_effort_{preset_extra_effort_epoch}"

            if motivation_mode == "Growth first":
                st.info("This deed will be recorded and appreciated, without points. Ordinary helpfulness does not need a prize.")
            elif motivation_mode == "Extra effort only":
                st.info(f"Suggested bonus if this was voluntary extra effort: {selected_deed['points']} points.")
                is_extra_effort = st.checkbox(
                    "This was voluntary extra effort, beyond an ordinary responsibility",
                    key=preset_extra_effort_key,
                )
            elif motivation_mode == "Points for every deed":
                st.info(f"This mode awards the suggested {selected_deed['points']} points for every recorded deed.")
            else:
                st.info("This deed will be recorded without points. Point rewards are turned off.")

            preset_note = st.text_area(
                "Optional note (what you noticed, not a score)",
                placeholder="Example: You noticed someone needed help and offered kindly.",
                key="preset_note",
            )

            if st.button(
                "✅ Record Good Deed",
                key="award_preset",
            ):
                awarded_points = add_deed(
                    selected_deed["name"],
                    selected_category,
                    selected_deed["points"],
                    preset_note,
                    is_extra_effort=is_extra_effort,
                )

                if awarded_points > 0:
                    st.success(f"Good deed recorded. {awarded_points} bonus points were added.")
                else:
                    st.success("Good deed recorded and appreciated. No points were attached.")
                st.session_state["preset_extra_effort_epoch"] = preset_extra_effort_epoch + 1
                st.rerun()

        elif record_deed_mode == "➕ Add / Award a Custom Good Deed":

            st.write(
                "Parents can create a new good deed "
                "that is not already in the list."
            )

            with st.form(
                "custom_deed_form"
            ):

                custom_name = st.text_input(
                    "Good deed name"
                )

                existing_categories = list(dict.fromkeys(
                    list(DEFAULT_DEEDS.keys())
                    + [
                        item.get("category", "")
                        for item in data.get("custom_deeds", [])
                        if item.get("category")
                    ]
                ))

                category_choice = st.selectbox(
                    "Category",
                    existing_categories
                    + ["➕ New Category"],
                )

                if category_choice == "➕ New Category":

                    custom_category = st.text_input(
                        "New category name"
                    )

                else:

                    custom_category = category_choice

                custom_points = st.number_input(
                    "Points",
                    min_value=1,
                    max_value=500,
                    value=20,
                    step=5,
                )

                custom_description = st.text_area(
                    "Optional note",
                    placeholder="What did you notice? Keep the note specific and encouraging.",
                )

                motivation_mode = data.get("settings", {}).get("motivation_mode", "Growth first")
                custom_extra_effort = False
                custom_extra_effort_epoch = st.session_state.get("custom_extra_effort_epoch", 0)
                if motivation_mode == "Extra effort only":
                    custom_extra_effort = st.checkbox(
                        "This was voluntary extra effort, beyond an ordinary responsibility",
                        key=f"custom_extra_effort_{custom_extra_effort_epoch}",
                    )
                elif motivation_mode == "Growth first":
                    st.caption("Growth first mode records this deed without points.")
                elif motivation_mode == "No points":
                    st.caption("No-points mode records this deed without points.")
                else:
                    st.caption("Points for every deed mode awards the suggested points.")

                save_custom = st.checkbox(
                    "Save this deed to the Good Deeds List "
                    "for future use",
                    value=True,
                )

                custom_submit = st.form_submit_button(
                    "⭐ Award Custom Good Deed"
                )

                if custom_submit:

                    final_category = (
                        custom_category.strip()
                    )

                    if not custom_name.strip():

                        st.error(
                            "Please enter a good deed name."
                        )

                    elif not final_category:

                        st.error(
                            "Please enter a category."
                        )

                    else:

                        awarded_points = add_deed(
                            custom_name.strip(),
                            final_category,
                            custom_points,
                            custom_description,
                            is_extra_effort=custom_extra_effort,
                        )

                        if save_custom:

                            duplicate = any(
                                d["name"].lower()
                                == custom_name.strip().lower()
                                and d["category"].lower()
                                == final_category.lower()
                                for d in data.get(
                                    "custom_deeds",
                                    [],
                                )
                            )

                            if not duplicate:

                                data[
                                    "custom_deeds"
                                ].append(
                                    {
                                        "name": custom_name.strip(),
                                        "category": final_category,
                                        "points": custom_points,
                                    }
                                )

                                save_data(data)

                        if awarded_points > 0:
                            st.success(f"Custom deed recorded. {awarded_points} bonus points were added.")
                        else:
                            st.success("Custom deed recorded and saved. No points were attached.")

                        st.session_state["custom_extra_effort_epoch"] = custom_extra_effort_epoch + 1
                        st.rerun()

        st.divider()



    with rewards_tab:
        st.caption("Create rewards and review approved reward redemptions.")
        st.subheader(
            "🛒 Add a New Reward"
        )

        with st.form(
            "reward_form"
        ):

            reward_name = st.text_input(
                "Reward Name"
            )

            reward_cost = st.number_input(
                "Point Cost",
                min_value=1,
                max_value=10000,
                value=100,
                step=10,
            )

            reward_emoji = st.text_input(
                "Emoji",
                value="🎁",
            )

            add_reward_button = st.form_submit_button(
                "Add Reward"
            )

            if add_reward_button:

                if reward_name.strip():

                    data.setdefault("rewards", []).append(
                        {
                            "name": reward_name.strip(),
                            "cost": int(reward_cost),
                            "emoji": (reward_emoji.strip() or "🎁"),
                        }
                    )

                    save_data(data)

                    st.success(
                        "🎁 Reward added successfully!"
                    )

                    st.rerun()

                else:

                    st.warning(
                        "Please enter a reward name."
                    )


        st.divider()
        st.subheader(
            "🎁 Reward History"
        )

        if data["redemptions"]:

            for redemption in data["redemptions"]:

                st.write(
                    f"🎁 **{redemption['reward']}** — "
                    f"{redemption['cost']} ⭐"
                )

                st.caption(
                    redemption["date"]
                )

        else:

            st.info(
                "No rewards have been redeemed yet."
            )



    with deeds_history_tab:
        st.caption("Browse the Good Deeds Library, complete deed history, and past approval reviews.")
        st.subheader(
            "📚 Good Deeds Library"
        )

        st.caption(
            "Browse deeds by category. Parent-created deeds "
            "are included automatically."
        )

        all_deeds = get_all_deeds_by_category()

        for category, deeds in all_deeds.items():

            with st.expander(
                f"{category}  ({len(deeds)} deeds)"
            ):

                for deed in deeds:

                    st.write(
                        f"• **{deed['name']}** — "
                        f"{deed['points']} ⭐"
                    )

        st.divider()

        st.subheader(
            "📋 Complete Good-Deed History"
        )

        if data["deeds"]:

            history_categories = [
                "All Categories"
            ] + sorted(
                set(
                    deed.get("category", "Uncategorised")
                    for deed in data["deeds"]
                )
            )

            history_filter = st.selectbox(
                "Filter history by category",
                history_categories,
            )

            filtered_history = data["deeds"]

            if history_filter != "All Categories":

                filtered_history = [
                    deed
                    for deed in data["deeds"]
                    if deed.get("category", "Uncategorised")
                    == history_filter
                ]

            for deed in filtered_history:

                earned = int(deed.get("points", 0) or 0)
                point_summary = f"+{earned} bonus points" if earned else "recorded without points"
                st.write(f"**{deed.get('name', 'Good deed')}** — {point_summary}")

                st.caption(
                    f"{deed.get('category', '')} • "
                    f"{deed.get('date', '')} • "
                    f"{deed.get('description', '')}"
                )

                st.divider()

        else:

            st.info(
                "No deeds have been recorded yet."
            )

        with st.expander("📜 Approval Review History"):
            child_review_history = data.get("child_deed_request_history", [])
            reward_review_history = data.get("reward_request_history", [])
            if child_review_history:
                st.markdown("**Child deed submissions**")
                for request in child_review_history[:20]:
                    st.write(f'**{request.get("name", "Good deed")}** — {request.get("status", "Reviewed")}')
                    if request.get("review_note"):
                        st.caption("Note: " + request["review_note"])
                    st.caption(request.get("reviewed_at", ""))
            if reward_review_history:
                st.markdown("**Reward requests**")
                for request in reward_review_history[:20]:
                    st.write(f'🎁 **{request.get("reward", "Reward")}** — {request.get("status", "Reviewed")} ({request.get("cost", 0)} ⭐)')
                    if request.get("review_note"):
                        st.caption("Note: " + request["review_note"])
                    st.caption(request.get("reviewed_at", ""))
            if not child_review_history and not reward_review_history:
                st.caption("No requests have been reviewed yet.")

        st.divider()



    with parent_settings_tab:
        st.caption("Change the Parent Dashboard password here. For appearance, goals, motivation, accessibility, and auto-lock preferences, open the ⚙️ Settings menu at the top-right.")
        st.subheader(
            "🔑 Change Parent Dashboard Password"
        )

        with st.form(
            "change_parent_password_form"
        ):

            current_password = st.text_input(
                "Current Parent Dashboard Password",
                type="password",
            )

            new_password = st.text_input(
                "New Parent Dashboard Password",
                type="password",
            )

            confirm_password = st.text_input(
                "Confirm New Parent Dashboard Password",
                type="password",
            )

            change_password = st.form_submit_button(
                "🔐 Change Parent Password"
            )

            if change_password:

                if not check_parent_password(
                    current_password
                ):

                    st.error(
                        "❌ Current Parent Dashboard password "
                        "is incorrect."
                    )

                elif len(new_password) < 8:

                    st.error(
                        "Please choose a new Parent Dashboard password "
                        "with at least 8 characters."
                    )

                elif new_password != confirm_password:

                    st.error(
                        "The two new passwords do not match."
                    )

                else:

                    data[
                        "parent_password_hash"
                    ] = hash_parent_password(
                        new_password
                    )

                    save_data(data)

                    st.success(
                        "✅ Parent Dashboard password "
                        "changed successfully."
                    )

        st.divider()


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "⭐ Good Deeds • Kindness matters, with or without points."
)

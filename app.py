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
from datetime import datetime

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

DATA_FILE = "good_deeds_data.json"
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
    "child_name": "Aarav",
    "parent_password_hash": "",
    "points": 0,
    "deeds": [],
    "redemptions": [],
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
# LOAD / SAVE
# =========================================================

def load_data():
    """Load family data and safely add defaults for new app versions."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                loaded = json.load(file)

            if not isinstance(loaded, dict):
                return copy.deepcopy(DEFAULT_DATA)

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

            for list_key in ("deeds", "redemptions", "custom_deeds", "reflections", "appreciations", "rewards"):
                if not isinstance(loaded.get(list_key), list):
                    loaded[list_key] = copy.deepcopy(DEFAULT_DATA[list_key])

            return loaded

        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            # Keep the app usable if the data file cannot be parsed.
            # Do not write defaults to disk automatically.
            return copy.deepcopy(DEFAULT_DATA)

    return copy.deepcopy(DEFAULT_DATA)


def save_data(data_to_save):
    """Write the JSON file atomically to reduce risk of partial saves."""
    temporary_file = DATA_FILE + ".tmp"
    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(data_to_save, file, indent=4, ensure_ascii=False)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary_file, DATA_FILE)


if "data" not in st.session_state:
    st.session_state.data = load_data()

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


def apply_saved_appearance():
    settings = data["settings"]
    preset_name = settings.get("theme_preset", "Light")

    if preset_name == "Custom":
        background = valid_hex_color(
            settings.get("custom_background"),
            "#FFFFFF",
        )
        sidebar = valid_hex_color(
            settings.get("custom_sidebar"),
            "#F8FAFC",
        )
        card = valid_hex_color(
            settings.get("custom_card"),
            "#F3F4F6",
        )
        text = valid_hex_color(
            settings.get("custom_text"),
            "#1F2937",
        )
    else:
        preset = THEME_PRESETS.get(
            preset_name,
            THEME_PRESETS["Light"],
        )
        background = preset["background"]
        sidebar = preset["sidebar"]
        card = preset["card"]
        text = preset["text"]

    accent = valid_hex_color(
        settings.get("accent_color"),
        "#4F46E5",
    )

    if settings.get("high_contrast", False):
        if preset_name == "Dark":
            background = "#000000"
            sidebar = "#000000"
            card = "#111111"
            text = "#FFFFFF"
        else:
            background = "#FFFFFF"
            sidebar = "#FFFFFF"
            card = "#FFFFFF"
            text = "#000000"

    font_family = FONT_FAMILIES.get(
        settings.get("font_family", "Sans"),
        FONT_FAMILIES["Sans"],
    )

    font_scale = safe_int(settings.get("font_scale", 100), 100, 85, 130)

    radius = safe_int(settings.get("card_radius", 15), 15, 0, 30)

    compact = bool(settings.get("compact_mode", False))
    large_controls = bool(settings.get("large_controls", False))
    reduce_motion = bool(settings.get("reduce_motion", False))
    shadows = bool(settings.get("card_shadows", True))

    block_gap = "0.45rem" if compact else "1rem"
    button_height = "3.1rem" if large_controls else "2.5rem"
    input_height = "3.1rem" if large_controls else "2.5rem"

    shadow_css = (
        "0 6px 18px rgba(0,0,0,0.14)"
        if shadows
        else "none"
    )

    motion_css = (
        "*, *::before, *::after {"
        "animation-duration: 0.001ms !important;"
        "animation-iteration-count: 1 !important;"
        "transition-duration: 0.001ms !important;"
        "scroll-behavior: auto !important;"
        "}"
        if reduce_motion
        else ""
    )

    st.markdown(
        f"""
        <style>
            :root {{
                --gd-accent: {accent};
                --gd-bg: {background};
                --gd-sidebar: {sidebar};
                --gd-card: {card};
                --gd-text: {text};
                --gd-radius: {radius}px;
            }}

            html, body, [class*="css"] {{
                font-family: {font_family} !important;
            }}

            .stApp,
            [data-testid="stAppViewContainer"] {{
                background: var(--gd-bg) !important;
                color: var(--gd-text) !important;
                font-size: {font_scale}% !important;
            }}

            [data-testid="stSidebar"] {{
                background: var(--gd-sidebar) !important;
            }}

            .stApp p,
            .stApp label,
            .stApp span,
            .stApp h1,
            .stApp h2,
            .stApp h3,
            .stApp h4,
            .stApp h5,
            .stApp h6,
            [data-testid="stMarkdownContainer"] {{
                color: var(--gd-text);
            }}

            .reward-card,
            .deed-card,
            .badge-card {{
                background: var(--gd-card) !important;
                color: var(--gd-text) !important;
                border-radius: var(--gd-radius) !important;
                box-shadow: {shadow_css} !important;
            }}

            .reward-card .reward-name,
            .reward-card .reward-cost,
            .deed-card b,
            .deed-card strong,
            .deed-card small,
            .badge-card b {{
                color: var(--gd-text) !important;
            }}

            div.stButton > button,
            div.stDownloadButton > button,
            button[kind="primary"] {{
                border-radius: var(--gd-radius) !important;
                min-height: {button_height};
            }}

            button[kind="primary"] {{
                background: var(--gd-accent) !important;
                border-color: var(--gd-accent) !important;
            }}

            div[data-baseweb="input"] > div,
            div[data-baseweb="select"] > div,
            textarea {{
                border-radius: var(--gd-radius) !important;
                min-height: {input_height};
            }}

            div[data-testid="stVerticalBlock"] {{
                gap: {block_gap};
            }}

            /* Compact three-dot settings control in the top-right header. */
            div[data-testid="stPopover"] > button {{
                min-width: 2.75rem !important;
                width: 2.75rem !important;
                min-height: 2.75rem !important;
                padding: 0 !important;
                font-size: 1.45rem !important;
                font-weight: 700 !important;
                border-radius: 12px !important;
                background: var(--gd-card) !important;
            }}

            .gd-motivation {{
                background: var(--gd-card);
                border-left: 5px solid var(--gd-accent);
                border-radius: var(--gd-radius);
                padding: 14px 16px;
                margin: 8px 0 18px 0;
                box-shadow: {shadow_css};
                color: var(--gd-text);
            }}

            {motion_css}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_saved_appearance()

# =========================================================
# REPLAY FIRST-TIME EXPERIENCE ONCE, WITHOUT WIPING FAMILY DATA
# =========================================================

if data.get(
    "onboarding_replay_version",
    0,
) < ONBOARDING_REPLAY_VERSION:

    # Preserve:
    # - points
    # - deed history
    # - custom good deeds
    # - rewards and reward history
    # - appearance/settings
    # - child's existing display name
    #
    # Reset only sign-in / onboarding credentials so this build behaves
    # like a fresh install one time.

    data["account_setup_complete"] = False

    data["account"] = {
        "login_type": "",
        "identifier": "",
        "country_code": "",
    }

    data["setup_complete"] = False
    data["parent_password_hash"] = ""
    data["parent_tour_completed"] = False

    # Mark replay as consumed immediately so Streamlit reruns do not
    # repeatedly reset the setup process.
    data["onboarding_replay_version"] = ONBOARDING_REPLAY_VERSION

    save_data(data)

    # Clear browser-session authentication too.
    st.session_state.logged_in = False
    st.session_state.parent_authenticated = False
    st.session_state.auth_stage = "identifier"
    st.session_state["dashboard_mode"] = "👦 Child Dashboard"
    st.session_state["parent_tour_step"] = 0

# =========================================================
# SECURITY HELPERS
# =========================================================

def hash_parent_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


def check_parent_password(password):
    stored_hash = data.get(
        "parent_password_hash",
        "",
    )

    return (
        bool(stored_hash)
        and hash_parent_password(password) == stored_hash
    )


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

if "auth_stage" not in st.session_state:
    st.session_state.auth_stage = "identifier"

# =========================================================
# LOGIN / REGISTRATION WITH OTP
# =========================================================

if not st.session_state.logged_in:

    st.markdown(
        '<div class="login-title">⭐ Good Deeds</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="login-subtitle">'
        "Sign in securely with a one-time code"
        "</div>",
        unsafe_allow_html=True,
    )

    left, centre, right = st.columns(
        [1, 1.5, 1]
    )

    with centre:

        account_exists = data.get(
            "account_setup_complete",
            False,
        )

        if st.session_state.auth_stage == "identifier":

            if account_exists:

                st.subheader("Sign in")

                saved_type = data.get(
                    "account",
                    {},
                ).get(
                    "login_type",
                    "email",
                )

                login_choices = (
                    ["📧 Email address"]
                    if saved_type == "email"
                    else ["📱 Phone number"]
                )

                login_type = login_choices[0]

            else:

                st.subheader("Create family account")

                login_type = st.radio(
                    "Continue using",
                    [
                        "📧 Email address",
                        "📱 Phone number",
                    ],
                    horizontal=True,
                )

            if login_type == "📧 Email address":

                email = st.text_input(
                    "Email address",
                    placeholder="parent@example.com",
                )

                identifier = email.strip().lower()
                country_code = ""
                chosen_type = "email"

            else:

                labels = list(
                    COUNTRY_CODES.keys()
                )

                saved_code = data.get(
                    "account",
                    {},
                ).get(
                    "country_code",
                    "+91",
                )

                default_index = 0

                for idx, label in enumerate(labels):
                    if COUNTRY_CODES[label] == saved_code:
                        default_index = idx
                        break

                country_label = st.selectbox(
                    "Country / region",
                    labels,
                    index=default_index,
                )

                country_code = COUNTRY_CODES[
                    country_label
                ]

                c1, c2 = st.columns(
                    [1, 3]
                )

                with c1:
                    st.text_input(
                        "Code",
                        value=country_code,
                        disabled=True,
                    )

                with c2:
                    phone = st.text_input(
                        "Phone number",
                        placeholder="9876543210",
                    )

                identifier = (
                    country_code
                    + clean_phone(phone)
                )

                chosen_type = "phone"

            if st.button(
                "Send OTP",
                type="primary",
                use_container_width=True,
            ):

                if chosen_type == "email":

                    if not valid_email(identifier):
                        st.error(
                            "Please enter a valid email address."
                        )
                        st.stop()

                else:

                    digits = clean_phone(
                        identifier
                    )

                    if len(digits) < 8 or len(digits) > 15:
                        st.error(
                            "Please enter a valid phone number."
                        )
                        st.stop()

                if account_exists:

                    saved_identifier = data.get(
                        "account",
                        {},
                    ).get(
                        "identifier",
                        "",
                    )

                    if not hmac.compare_digest(
                        identifier,
                        saved_identifier,
                    ):
                        st.error(
                            "That email address or phone number "
                            "is not registered."
                        )
                        st.stop()

                st.session_state.pending_identifier = identifier
                st.session_state.pending_login_type = chosen_type
                st.session_state.pending_country_code = country_code

                issue_otp(identifier)

                st.session_state.auth_stage = "otp"

                st.rerun()

        else:

            identifier = st.session_state.get(
                "pending_identifier",
                "",
            )

            st.subheader("Enter your OTP")

            st.write(
                f"We created a 6-digit code for **{identifier}**."
            )

            # LOCAL DEVELOPMENT ONLY
            st.warning(
                "🧪 Testing mode: because this app is running locally "
                "and is not connected to an email/SMS service yet, "
                "your OTP is shown below."
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

                    if not data.get(
                        "account_setup_complete",
                        False,
                    ):

                        data["account"] = {
                            "login_type": st.session_state.get(
                                "pending_login_type",
                                "email",
                            ),
                            "identifier": identifier,
                            "country_code": st.session_state.get(
                                "pending_country_code",
                                "",
                            ),
                        }

                        data["account_setup_complete"] = True

                        save_data(data)

                    st.session_state.logged_in = True
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
        "Your email/phone has been verified. Now a parent or guardian "
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

            elif len(parent_password) < 4:

                st.error(
                    "Please choose a Parent Dashboard password "
                    "with at least 4 characters."
                )

            elif parent_password != confirm_parent_password:

                st.error(
                    "The two Parent Dashboard passwords do not match."
                )

            else:

                data["child_name"] = child_name.strip()

                data["parent_password_hash"] = (
                    hash_parent_password(
                        parent_password
                    )
                )

                data["setup_complete"] = True

                save_data(data)

                st.session_state.parent_authenticated = True
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
        "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
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
    try:
        current_points = max(0, int(data.get("points", 0)))
        reward_cost = max(0, int(reward.get("cost", 0)))
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False

    if reward_cost <= 0 or current_points < reward_cost:
        return False

    data["points"] = current_points - reward_cost
    redemption = {
        "reward": str(reward.get("name", "Reward")),
        "cost": reward_cost,
        "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
    }
    data.setdefault("redemptions", []).insert(0, redemption)
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
        "Personalise the app. Changes are saved on this device."
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

    if st.session_state.get("parent_authenticated", False):
        if st.button(
            "🔒 Lock Parent Dashboard",
            use_container_width=True,
        ):
            st.session_state.parent_authenticated = False
            st.session_state["dashboard_mode"] = "👦 Child Dashboard"
            st.rerun()

    if st.button(
        "🚪 Log Out",
        use_container_width=True,
    ):

        st.session_state.logged_in = False
        st.session_state.parent_authenticated = False
        st.session_state.auth_stage = "identifier"
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
            "Recording a deed is about noticing behaviour; it does not have to create a score.",
            "Appreciation notes are private encouragement and never award points.",
        ],
    },
    {
        "title": "2. Choose your family's motivation approach",
        "body": "Open the ⋮ menu at the top-right and find Motivation & rewards in Settings. The default is Growth first, so new deeds are recorded without automatically earning points.",
        "bullets": [
            "Growth first: deeds are recorded without points; the rewards shop is hidden.",
            "Extra effort only: points are awarded only when a parent explicitly marks a deed as voluntary extra effort.",
            "Points for every deed: keeps the traditional points system.",
            "No points: tracks deeds, reflections and appreciation without point rewards.",
        ],
    },
    {
        "title": "3. Personalise appearance",
        "body": "The ⋮ menu opens Settings. Changes take effect after you select Save Settings.",
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
        "body": "The app currently saves family data in good_deeds_data.json in the folder where the app runs. Keep a backup before moving the app to another computer.",
        "bullets": [
            "Use the privacy toggle to hide or show the signed-in email/phone in the sidebar.",
            "Export family data creates a JSON backup including deeds, rewards, reflections, appreciation notes and settings; it excludes passwords and account credentials.",
            "Use Replay Parent Welcome Tour in Settings to see this guide again.",
            "Use Lock Parent Dashboard when stepping away, and Log Out when finished.",
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
        st.caption("You will see this guide once. You can replay it later from the ⋮ Settings menu.")
        st.progress(
            (step_index + 1) / len(PARENT_TOUR_STEPS),
            text=f"Step {step_index + 1} of {len(PARENT_TOUR_STEPS)}",
        )
        st.subheader(step["title"])
        st.write(step["body"])
        for bullet in step["bullets"]:
            st.markdown(f"- {bullet}")

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
    with st.popover("⋮", help="Settings, appearance, accessibility and data tools"):
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

mode = st.sidebar.radio(
    "Choose Dashboard",
    [
        "👦 Child Dashboard",
        "👨‍👩‍👦 Parent Dashboard",
    ],
    key="dashboard_mode",
)

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

                st.rerun()

            else:

                st.sidebar.error(
                    "❌ Incorrect Parent Dashboard password."
                )

    else:

        st.sidebar.success(
            "✅ Parent access unlocked."
        )

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

    st.info(
        "Enter the Parent Dashboard password in the sidebar to continue."
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

    if settings.get(
        "show_badges",
        True,
    ):

        st.subheader(
            "🏅 Your Badges"
        )

        badges = get_badges()

        if badges:

            badge_cols = st.columns(
                len(badges)
            )

            for i, badge in enumerate(
                badges
            ):

                with badge_cols[i]:

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
                    "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
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

        for start in range(
            0,
            len(data["rewards"]),
            3,
        ):

            reward_cols = st.columns(3)

            for offset, reward in enumerate(
                data["rewards"][
                    start:start + 3
                ]
            ):

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
                        f"Redeem for {reward_cost} ⭐",
                        key=f"reward_{i}",
                    ):

                        if redeem_reward(
                            reward
                        ):

                            st.success(
                                f"🎉 You redeemed: "
                                f"{reward['name']}!"
                            )

                            st.rerun()

                        else:

                            st.info(
                                "There are not enough points for this reward right now. "
                                "A good deed is still worthwhile without a reward."
                            )

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

    st.divider()
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
                "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
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

    st.subheader(
        "⭐ Record a Good Deed"
    )

    preset_tab, custom_tab = st.tabs(
        [
            "📋 Choose from Good Deeds List",
            "➕ Add / Award a Custom Good Deed",
        ]
    )

    with preset_tab:

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

    with custom_tab:

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

    st.divider()

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

            elif len(new_password) < 4:

                st.error(
                    "Please choose a new Parent Dashboard password "
                    "with at least 4 characters."
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

# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "⭐ Good Deeds • Kindness matters, with or without points."
)
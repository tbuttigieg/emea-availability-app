import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz # Library for timezone handling
from collections import defaultdict

# --- CONFIGURATION ---
# TEAM_DATA has been programmatically generated from the 'OBS' Google Sheet tab.
TEAM_DATA = [
    {
        "name": "Amina Maachoui",
        "userUri": "",
        "soloEventUri": "",
        "languages": ["English", "French"],
        "team": "EMEA",
        "active": False
    },
    {
        "name": "Angelique Berry",
        "userUri": "https://api.calendly.com/users/BFGD5IENSLHBGKCA",
        "soloEventUri": "https://api.calendly.com/event_types/69ab400d-beb3-4ec1-9fec-692834cca779",
        "languages": ["English"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Dennis Piethe",
        "userUri": "https://api.calendly.com/users/HHAHQ36MF72PWSDJ",
        "soloEventUri": "https://api.calendly.com/event_types/75b9658e-71ee-4a74-9458-ca60b4c527fa",
        "languages": ["English", "German"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Harry Britten",
        "userUri": "https://api.calendly.com/users/0db643a2-44f4-46e1-ac2b-ece863b5045d",
        "soloEventUri": "https://api.calendly.com/event_types/c2a5c4df-4895-4b0c-ab71-4e3c64ab0e2d",
        "languages": ["English", "French"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Izabella Ferencz",
        "userUri": "https://api.calendly.com/users/BCHFHLGAUO5OTUFG",
        "soloEventUri": "https://api.calendly.com/event_types/05722fb1-5d63-4fa9-9795-413240c72816",
        "languages": ["English", "French", "Spanish"],
        "team": "EMEA",
        "active": False
    },
    {
        "name": "Jair Eastbury",
        "userUri": "https://api.calendly.com/users/DBDGGHZOPYXBMELD",
        "soloEventUri": "https://api.calendly.com/event_types/c3a8471d-321a-42e7-be7f-0899b84223f5",
        "languages": ["English"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Karin Anders",
        "userUri": "https://api.calendly.com/users/DEGHPMACPCLOCLAA",
        "soloEventUri": "https://api.calendly.com/event_types/6778bb57-bd8c-4e57-8b2b-5c51de95acbd",
        "languages": ["English", "German"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Malik Vazirna-Singh",
        "userUri": "https://api.calendly.com/users/EDGGEI7F6COAYX3E",
        "soloEventUri": "https://api.calendly.com/event_types/cb749cea-8128-43a4-bb66-46427f6b4d4c",
        "languages": ["English", "French", "Spanish", "Italian"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Natali Lilovska",
        "userUri": "https://api.calendly.com/users/eb2c8c12-bdc3-49ec-a3c4-f11ef0b72e7e",
        "soloEventUri": "https://api.calendly.com/event_types/0a8c2cdf-2255-4a0a-b081-d8fb69584b78",
        "languages": ["English", "German"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Nina Leist",
        "userUri": "https://api.calendly.com/users/EAGAHVEPVZKHOGGB",
        "soloEventUri": "https://api.calendly.com/event_types/75f3f3a1-a4e0-4659-8fb8-efefadcd48b9",
        "languages": ["English", "Spanish", "German", "Italian"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Sara Pomparelli",
        "userUri": "https://api.calendly.com/users/b0b405a2-dcf8-4e9f-badc-1de47683400a",
        "soloEventUri": "https://api.calendly.com/event_types/5464d38a-10bc-4ede-ba84-6f924b5e98e6",
        "languages": ["English", "Spanish", "Italian"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Shamika Alphons ",
        "userUri": "https://api.calendly.com/users/FHDGBJ2IF6MEFNGQ",
        "soloEventUri": "https://api.calendly.com/event_types/6bfc26c7-dc18-48fa-a757-ba670b012446",
        "languages": ["English", "German"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Victor Cabrera",
        "userUri": "https://api.calendly.com/users/GFEFGA4NO2WXJVA5",
        "soloEventUri": "https://api.calendly.com/event_types/67d128a6-5817-4967-ae85-9fba44012703",
        "languages": ["English", "Spanish"],
        "team": "EMEA",
        "active": True
    }
]

TEAM_TO_REPORT = 'EMEA'
WORKING_DAYS_TO_CHECK = 14
MINIMUM_NOTICE_HOURS = 21
SLOT_DURATION_MINUTES = 120
ADMIN_PASSWORD = "WinAsOne" # <-- Easy to change password here

# New curated lists for the dropdowns
LANGUAGES = ["English", "German", "French", "Italian", "Spanish"]
TIMEZONE_OPTIONS = {
    "GMT / BST (London, Dublin)": "Europe/London",
    "CET (Paris, Berlin, Rome)": "Europe/Paris",
    "EET (Athens, Helsinki)": "Europe/Helsinki",
    "GST (Dubai, Abu Dhabi)": "Asia/Dubai",
    "EST (New York, Toronto)": "America/New_York",
    "CST (Chicago, Mexico City)": "America/Chicago",
    "MST (Denver, Phoenix)": "America/Denver",
    "PST (Los Angeles, Vancouver)": "America/Los_Angeles",
}
DEFAULT_TIMEZONE_FRIENDLY = "GMT / BST (London, Dublin)"

# --- CORE FUNCTIONS ---

def get_filtered_team_members():
    """Filters the hardcoded TEAM_DATA list."""
    return [
        m for m in TEAM_DATA
        if m["active"] and m["team"] == TEAM_TO_REPORT and m["userUri"] and m["soloEventUri"]
    ]

@st.cache_data(ttl=600) # Cache the data for 10 minutes
def get_user_availability(solo_event_uri, start_date, end_date, api_key):
    """Fetches available slots from the Calendly API, looping in 7-day chunks."""
    if not api_key:
        st.error("Calendly API Key is not set. Please add it to your secrets.toml file.")
        return []

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    all_slots = []
    base_url = "https://api.calendly.com/event_type_available_times"

    def format_to_iso_z(dt):
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    loop_start_date = start_date
    while loop_start_date < end_date:
        loop_end_date = loop_start_date + timedelta(days=7)
        if loop_end_date > end_date:
            loop_end_date = end_date

        params = {
            'event_type': solo_event_uri,
            'start_time': format_to_iso_z(loop_start_date),
            'end_time': format_to_iso_z(loop_end_date)
        }

        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for slot in data.get("collection", []):
                if slot.get("status") == "available":
                    start_time_str = slot["start_time"]
                    if start_time_str.endswith('Z'):
                        start_time_str = start_time_str[:-1] + '+00:00'
                    all_slots.append(datetime.fromisoformat(start_time_str))

        except requests.exceptions.HTTPError as e:
            # Silently fail for the admin view to avoid clutter
            pass
        
        loop_start_date += timedelta(days=7)

    return all_slots


def fetch_language_availability(team_members, api_key, selected_language):
    """Fetches and organizes availability data for a single, selected language."""
    utc = pytz.UTC
    now = datetime.now(utc)
    minimum_booking_time = now + timedelta(hours=MINIMUM_NOTICE_HOURS)
    api_start_date = now + timedelta(minutes=1)
    api_end_date = api_start_date + timedelta(days=WORKING_DAYS_TO_CHECK)

    language_slots = []
    members_for_lang = [m for m in team_members if selected_language in m["languages"]]
    
    for member in members_for_lang:
        user_slots = get_user_availability(member["soloEventUri"], api_start_date, api_end_date, api_key)
        
        for slot_time in user_slots:
            if slot_time >= minimum_booking_time:
                language_slots.append({
                    "specialist": member["name"],
                    "dateTime": slot_time 
                })
    
    language_slots.sort(key=lambda x: x["dateTime"])
    return language_slots

def fetch_all_team_availability(team_members, api_key):
    """New function to fetch availability for every team member for the admin view."""
    utc = pytz.UTC
    now = datetime.now(utc)
    api_start_date = now + timedelta(minutes=1)
    api_end_date = api_start_date + timedelta(days=WORKING_DAYS_TO_CHECK)
    
    availability_by_specialist = defaultdict(list)

    for member in team_members:
        user_slots = get_user_availability(member["soloEventUri"], api_start_date, api_end_date, api_key)
        for slot_time in user_slots:
            availability_by_specialist[member["name"]].append(slot_time)
            
    return availability_by_specialist


def calculate_true_slots(date_times):
    """Calculates non-overlapping slots."""
    if not date_times:
        return 0
    
    date_times.sort()
    slot_duration = timedelta(minutes=SLOT_DURATION_MINUTES)
    count = 0
    last_booked_end_time = datetime.min.replace(tzinfo=pytz.UTC)

    for start_time in date_times:
        if start_time >= last_booked_end_time:
            count += 1
            last_booked_end_time = start_time + slot_duration
            
    return count

# --- STREAMLIT UI ---

st.set_page_config(layout="wide")
st.title("EMEA Onboarding Team Availability")

# --- Initialize session state for password ---
if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

# --- Sidebar for user inputs ---
st.sidebar.header("Options")

selected_language = st.sidebar.selectbox(
    "Select language",
    options=LANGUAGES
)

selected_timezone_friendly = st.sidebar.selectbox(
    "Select your timezone",
    options=TIMEZONE_OPTIONS.keys(),
    index=list(TIMEZONE_OPTIONS.keys()).index(DEFAULT_TIMEZONE_FRIENDLY)
)
selected_timezone_str = TIMEZONE_OPTIONS[selected_timezone_friendly]
selected_timezone = pytz.timezone(selected_timezone_str)

if st.sidebar.button("Refresh Availability"):
    team_members = get_filtered_team_members()
    if not team_members:
        st.warning(f"No active members found for the '{TEAM_TO_REPORT}' team.")
    else:
        with st.spinner(f"Fetching availability for {selected_language}..."):
            calendly_api_key = st.secrets.get("CALENDLY_API_KEY")
            all_slots = fetch_language_availability(team_members, calendly_api_key, selected_language)

        if not all_slots:
            st.info(f"No upcoming availability found for **{selected_language}** in the next {WORKING_DAYS_TO_CHECK} days.")
        else:
            slots_by_day = defaultdict(list)
            for slot in all_slots:
                local_time = slot["dateTime"].astimezone(selected_timezone)
                day = local_time.date()
                if day.weekday() < 5:
                    slots_by_day[day].append(slot)

            st.header(f"Available Slots for {selected_language}")
            st.write(f"Times are shown in **{selected_timezone_friendly}**.")
            st.divider()

            sorted_days = sorted(slots_by_day.keys())

            for day in sorted_days:
                st.subheader(day.strftime('%A, %d %B %Y'))
                day_slots = slots_by_day[day]
                unique_times = sorted(list(set(s['dateTime'].astimezone(selected_timezone).strftime('%H:%M') for s in day_slots)))
                
                if not unique_times:
                    st.text("No slots available on this day.")
                    continue

                cols = st.columns(5)
                for i, time_str in enumerate(unique_times):
                    with cols[i % 5]:
                        st.markdown(f"<div style='text-align: center; border: 1px solid #e0e0e0; border-radius: 5px; padding: 10px; margin-bottom: 10px;'><b>{time_str}</b></div>", unsafe_allow_html=True)
                st.divider()

            st.header("Summary of Daily Availability")
            summary_data = []
            for day in sorted_days:
                day_slots = slots_by_day[day]
                slots_by_specialist = defaultdict(list)
                for slot in day_slots:
                    slots_by_specialist[slot['specialist']].append(slot['dateTime'])
                total_true_slots_for_day = 0
                for specialist_name, specialist_slots in slots_by_specialist.items():
                    total_true_slots_for_day += calculate_true_slots(specialist_slots)
                summary_data.append({
                    "Date": day.strftime('%A, %d %B'),
                    f"Bookable {SLOT_DURATION_MINUTES}-min Slots": total_true_slots_for_day
                })
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
else:
    st.info("Select your options and click 'Refresh Availability' in the sidebar.")


# --- Admin Section ---
st.sidebar.divider()
st.sidebar.header("Admin Access")
password = st.sidebar.text_input("Enter password for detailed view", type="password", key="password_input")

if st.sidebar.button("Unlock Detailed View"):
    if password == ADMIN_PASSWORD:
        st.session_state['admin_authenticated'] = True
    else:
        st.sidebar.error("Incorrect password.")
        st.session_state['admin_authenticated'] = False

if st.session_state.get('admin_authenticated'):
    st.sidebar.success("Admin view unlocked!")
    st.divider()
    st.header("🔒 Admin View: Detailed Specialist Availability")
    
    team_members = get_filtered_team_members()
    with st.spinner("Fetching all team availability..."):
        calendly_api_key = st.secrets.get("CALENDLY_API_KEY")
        admin_availability = fetch_all_team_availability(team_members, calendly_api_key)

    if not admin_availability:
        st.warning("No availability found for any team member.")
    else:
        uk_timezone = pytz.timezone("Europe/London")
        sorted_specialists = sorted(admin_availability.keys())

        for specialist in sorted_specialists:
            with st.expander(f"**{specialist}** - {len(admin_availability[specialist])} available slots"):
                slots = admin_availability[specialist]
                if not slots:
                    st.write("No availability in the upcoming period.")
                    continue
                
                slots_by_day = defaultdict(list)
                for slot_time_utc in slots:
                    local_time = slot_time_utc.astimezone(uk_timezone)
                    day = local_time.date()
                    if day.weekday() < 5: # Monday-Friday
                        slots_by_day[day].append(local_time)

                if not slots_by_day:
                    st.write("No availability on upcoming weekdays.")
                    continue
                    
                sorted_days = sorted(slots_by_day.keys())
                for day in sorted_days:
                    st.markdown(f"**{day.strftime('%A, %d %B')}**")
                    day_slots = sorted(slots_by_day[day])
                    time_strings = [f"`{s.strftime('%H:%M')}`" for s in day_slots]
                    st.write(" | ".join(time_strings))


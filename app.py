import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz # Library for timezone handling
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor # For parallel API calls

# --- CONFIGURATION ---
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
        "languages": ["English", "French"], # Spanish removed
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
        "languages": ["English", "Spanish", "German", "Italian", "French"], # French added
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Sara Pomparelli",
        "userUri": "https://api.calendly.com/users/b0b405a2-dcf8-4e9f-badc-1de47683400a",
        "soloEventUri": "https://api.calendly.com/event_types/5464d38a-10bc-4ede-ba84-6f924b5e98e6",
        "languages": ["English", "Italian"], # Spanish removed
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Shamika Alphons",
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
WORKING_DAYS_TO_CHECK = 10 
MINIMUM_NOTICE_HOURS = 21
SLOT_DURATION_MINUTES = 120
ADMIN_PASSWORD = "WinAsOne" 
WORKING_HOURS_START = 9
WORKING_HOURS_END = 17

LANGUAGES = ["English", "German", "French", "Italian", "Spanish"]
TIMEZONE_OPTIONS = {
    "GMT / BST (London, Dublin)": "Europe/London",
    "CET (Paris, Berlin, Rome)": "Europe/Paris",
    "EET (Athens, Helsinki)": "Europe/Helsinki",
    "GST (Dubai, Abu Dhabi)": "Asia/Dubai",
}
DEFAULT_TIMEZONE_FRIENDLY = "GMT / BST (London, Dublin)"

# --- CORE FUNCTIONS ---

def get_filtered_team_members():
    """Filters the hardcoded TEAM_DATA list."""
    return [
        m for m in TEAM_DATA
        if m["active"] and m["team"] == TEAM_TO_REPORT and m["userUri"] and m["soloEventUri"]
    ]

@st.cache_data(ttl=600)
def get_user_availability(solo_event_uri, start_date, end_date, api_key):
    """Fetches available slots from the Calendly API for a single user."""
    if not api_key: return []

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    all_slots = []
    base_url = "https://api.calendly.com/event_type_available_times"

    def format_to_iso_z(dt):
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    loop_start_date = start_date
    while loop_start_date < end_date:
        loop_end_date = loop_start_date + timedelta(days=7)
        if loop_end_date > end_date: loop_end_date = end_date

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
                    start_time_str = slot["start_time"].replace('Z', '+00:00')
                    all_slots.append(datetime.fromisoformat(start_time_str))
        except requests.exceptions.HTTPError: pass
        loop_start_date += timedelta(days=7)
    return all_slots

def fetch_language_availability(team_members, api_key, selected_language):
    """Fetches availability for a single language using concurrent API calls for speed."""
    utc, now = pytz.UTC, datetime.now(pytz.UTC)
    minimum_booking_time = now + timedelta(hours=MINIMUM_NOTICE_HOURS)
    api_start_date = now + timedelta(minutes=1)
    api_end_date = api_start_date + timedelta(days=WORKING_DAYS_TO_CHECK + 4) 

    language_slots = []
    members_for_lang = [m for m in team_members if selected_language in m["languages"]]
    
    with ThreadPoolExecutor(max_workers=len(members_for_lang) or 1) as executor:
        args = [(m["soloEventUri"], api_start_date, api_end_date, api_key) for m in members_for_lang]
        results = executor.map(lambda p: get_user_availability(*p), args)
        for member, user_slots in zip(members_for_lang, results):
            for slot_time in user_slots:
                if slot_time >= minimum_booking_time:
                    language_slots.append({"specialist": member["name"], "dateTime": slot_time})
    language_slots.sort(key=lambda x: x["dateTime"])
    return language_slots

def fetch_all_team_availability(team_members, api_key):
    """Fetches availability for all team members concurrently, applying the minimum notice period."""
    utc, now = pytz.UTC, datetime.now(pytz.UTC)
    minimum_booking_time = now + timedelta(hours=MINIMUM_NOTICE_HOURS)
    api_start_date = now + timedelta(minutes=1)
    api_end_date = api_start_date + timedelta(days=WORKING_DAYS_TO_CHECK + 4)
    
    availability_by_specialist = defaultdict(list)
    raw_slots_for_summary = []

    with ThreadPoolExecutor(max_workers=len(team_members) or 1) as executor:
        args = [(m, api_start_date, api_end_date, api_key) for m in team_members]
        
        def fetch_and_process(member, start, end, key):
            slots = get_user_availability(member["soloEventUri"], start, end, key)
            return member, slots

        results = executor.map(lambda p: fetch_and_process(*p), args)

        for member, user_slots in results:
            for slot_time in user_slots:
                if slot_time >= minimum_booking_time:
                    availability_by_specialist[member["name"]].append(slot_time)
                    raw_slots_for_summary.append({"specialist_info": member, "dateTime": slot_time})

    return availability_by_specialist, raw_slots_for_summary


def calculate_true_slots(date_times):
    """Calculates non-overlapping slots."""
    if not date_times: return 0
    date_times.sort()
    slot_duration = timedelta(minutes=SLOT_DURATION_MINUTES)
    count = 0
    last_booked_end_time = datetime.min.replace(tzinfo=pytz.UTC)
    for start_time in date_times:
        if start_time >= last_booked_end_time:
            count += 1
            last_booked_end_time = start_time + slot_duration
    return count

def get_next_working_days(n, timezone):
    """Gets the next N working days."""
    days = []
    current_day = datetime.now(timezone).date()
    while len(days) < n:
        if current_day.weekday() < 5:
            days.append(current_day)
        current_day += timedelta(days=1)
    return days

# --- STREAMLIT UI ---

st.set_page_config(layout="wide")
st.title("EMEA Onboarding Team Availability")

if 'admin_authenticated' not in st.session_state: st.session_state['admin_authenticated'] = False

st.sidebar.header("Options")
selected_language = st.sidebar.selectbox("Select language", options=LANGUAGES)
selected_timezone_friendly = st.sidebar.selectbox("Select your timezone", options=TIMEZONE_OPTIONS.keys(), index=list(TIMEZONE_OPTIONS.keys()).index(DEFAULT_TIMEZONE_FRIENDLY))
selected_timezone = pytz.timezone(TIMEZONE_OPTIONS[selected_timezone_friendly])

if st.sidebar.button("Refresh Availability"):
    team_members = get_filtered_team_members()
    if not team_members:
        st.warning(f"No active members found for the '{TEAM_TO_REPORT}' team.")
    else:
        with st.spinner(f"Fetching availability for {selected_language}..."):
            calendly_api_key = st.secrets.get("CALENDLY_API_KEY")
            all_slots = fetch_language_availability(team_members, calendly_api_key, selected_language)

        if not all_slots:
            st.info(f"No upcoming availability found for **{selected_language}** in the next {WORKING_DAYS_TO_CHECK} working days.")
        else:
            slots_by_day = defaultdict(list)
            working_days = get_next_working_days(WORKING_DAYS_TO_CHECK, selected_timezone)
            for slot in all_slots:
                day = slot["dateTime"].astimezone(selected_timezone).date()
                if day in working_days:
                    slots_by_day[day].append(slot)
            
            if not slots_by_day:
                 st.info(f"No upcoming availability found for **{selected_language}** in the next {WORKING_DAYS_TO_CHECK} working days.")
                 st.stop()

            st.header(f"Available Slots for {selected_language}")
            st.write(f"Times are shown in **{selected_timezone_friendly}**.")
            st.divider()
            for day in working_days:
                if day in slots_by_day:
                    st.subheader(day.strftime('%A, %d %B %Y'))
                    day_slots = slots_by_day[day]
                    unique_times = sorted(list(set(s['dateTime'].astimezone(selected_timezone).strftime('%H:%M') for s in day_slots)))
                    cols = st.columns(5)
                    for i, time_str in enumerate(unique_times):
                        cols[i % 5].markdown(f"<div style='text-align: center; border: 1px solid #e0e0e0; border-radius: 5px; padding: 10px; margin-bottom: 10px;'><b>{time_str}</b></div>", unsafe_allow_html=True)
                    st.divider()

            st.header("Summary of Daily Availability")
            summary_data = []
            for day in working_days:
                 if day in slots_by_day:
                    day_slots = slots_by_day[day]
                    slots_by_specialist = defaultdict(list)
                    for slot in day_slots:
                        slots_by_specialist[slot['specialist']].append(slot['dateTime'])
                    total_true_slots = sum(calculate_true_slots(s_slots) for s_slots in slots_by_specialist.values())
                    summary_data.append({"Date": day.strftime('%A, %d %B'), "Bookable Slots": total_true_slots})
            if summary_data:
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
else:
    st.info("Select your options and click 'Refresh Availability' in the sidebar.")

# --- Admin Section ---
st.sidebar.divider()
st.sidebar.header("Admin Access")
password = st.sidebar.text_input("Enter password", type="password")

if st.sidebar.button("Unlock Admin View"):
    if password == ADMIN_PASSWORD:
        st.session_state['admin_authenticated'] = True
    else:
        st.sidebar.error("Incorrect password.")
        st.session_state['admin_authenticated'] = False

if st.session_state.get('admin_authenticated'):
    st.sidebar.success("Admin view unlocked!")
    st.divider()
    st.header("🔒 Admin View")
    
    active_team_members = get_filtered_team_members()
    with st.spinner("Fetching all team availability for admin view..."):
        calendly_api_key = st.secrets.get("CALENDLY_API_KEY")
        admin_availability, raw_slots = fetch_all_team_availability(active_team_members, calendly_api_key)
    
    if not admin_availability:
        st.warning("No availability found for any team member.")
    else:
        uk_timezone = pytz.timezone("Europe/London")
        working_days = get_next_working_days(WORKING_DAYS_TO_CHECK, uk_timezone)
        
        st.subheader("Team Summary by Language")
        st.write("Total bookable slots for the entire team.")
        
        lang_summary_slots = defaultdict(lambda: defaultdict(int))
        slots_by_specialist_day = defaultdict(lambda: defaultdict(list))

        for slot in raw_slots:
            day = slot['dateTime'].astimezone(uk_timezone).date()
            if day in working_days:
                specialist_name = slot['specialist_info']['name']
                slots_by_specialist_day[specialist_name][day].append(slot['dateTime'])
        
        for specialist, day_slots in slots_by_specialist_day.items():
            specialist_info = next((m for m in active_team_members if m['name'] == specialist), None)
            if specialist_info:
                for day, slots in day_slots.items():
                    true_slots = calculate_true_slots(slots)
                    for lang in specialist_info['languages']:
                        lang_summary_slots[lang][day] += true_slots

        summary_data = []
        for lang in LANGUAGES:
            row = {"Language": lang}
            for day in working_days:
                day_str = day.strftime('%a %d/%m')
                row[day_str] = lang_summary_slots[lang].get(day, 0)
            summary_data.append(row)
        summary_df = pd.DataFrame(summary_data).set_index("Language")

        # --- UPDATE: New summary table coloring ---
        def color_summary_cells(val):
            if val == 0:
                return 'background-color: #ffcccb'  # Light Red
            elif 1 <= val <= 4:
                return 'background-color: #d4edda'  # Light Green
            else: # 5+
                return 'background-color: #28a745; color: white;' # Dark Green

        st.dataframe(summary_df.style.applymap(color_summary_cells), use_container_width=True)
        st.divider()

        st.subheader("Team Capacity Heatmap")
        st.write("A visual overview of each specialist's bookable slots per day.")
        heatmap_data = defaultdict(lambda: {day.strftime('%a %d/%m'): 0 for day in working_days})
        for specialist, slots in admin_availability.items():
            slots_by_day = defaultdict(list)
            for slot_time in slots:
                day = slot_time.astimezone(uk_timezone).date()
                if day in working_days:
                    slots_by_day[day].append(slot_time)
            for day, day_slots in slots_by_day.items():
                heatmap_data[specialist][day.strftime('%a %d/%m')] = calculate_true_slots(day_slots)
        heatmap_df = pd.DataFrame(heatmap_data).T
        
        def color_heatmap_cells(val):
            if val == 0:
                return 'background-color: #ffcccb'
            elif 1 <= val <= 2:
                return 'background-color: #d4edda'
            else:
                return 'background-color: #28a745; color: white;'
        
        st.dataframe(heatmap_df.style.applymap(color_heatmap_cells), use_container_width=True)
        st.divider()

        st.subheader("Detailed Specialist Availability")
        sorted_specialists = sorted(admin_availability.keys())
        for specialist in sorted_specialists:
            with st.expander(f"**{specialist}** - {len(admin_availability[specialist])} available slots found"):
                slots = admin_availability[specialist]
                if not slots:
                    st.write("No availability in the upcoming period.")
                    continue
                slots_by_day = defaultdict(list)
                for slot_time_utc in slots:
                    day = slot_time_utc.astimezone(uk_timezone).date()
                    if day in working_days:
                        slots_by_day[day].append(slot_time_utc.astimezone(uk_timezone))
                
                if not slots_by_day:
                    st.write("No availability on upcoming weekdays.")
                    continue

                for day in working_days:
                     if day in slots_by_day:
                        st.markdown(f"**{day.strftime('%A, %d %B')}**")
                        day_slots = sorted(slots_by_day[day])
                        time_strings = [f"`{s.strftime('%H:%M')}`" for s in day_slots]
                        st.write(" | ".join(time_strings))


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
        "userUri": "https://api.calendly.com/users/c4fc4718-ed3d-4281-9035-d606f2b09ea0",
        "soloEventUri": "", # TODO: Add soloEventUri
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
        "languages": ["English", "French"],
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
        "languages": ["English", "Spanish", "German", "Italian", "French"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Sara Pomparelli",
        "userUri": "https://api.calendly.com/users/b0b405a2-dcf8-4e9f-badc-1de47683400a",
        "soloEventUri": "https://api.calendly.com/event_types/5464d38a-10bc-4ede-ba84-6f924b5e98e6",
        "languages": ["English", "Italian"],
        "team": "EMEA",
        "active": True
    },
    {
        "name": "Sarah Jopp",
        "userUri": "https://api.calendly.com/users/269b9b21-5e44-41d1-b641-4f48c6549cfe",
        "soloEventUri": "https://api.calendly.com/event_types/cf5f3c50-5956-4e9b-832e-074d09dcfb3e",
        "languages": ["English"],
        "team": "EMEA",
        "active": False
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
        "name": "Tom Webb",
        "userUri": "", # TODO: Add userUri
        "soloEventUri": "", # TODO: Add soloEventUri
        "languages": ["English", "German"],
        "team": "EMEA",
        "active": False
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
WORKING_DAYS_TO_CHECK = 7 
MINIMUM_NOTICE_HOURS = 21
SLOT_DURATION_MINUTES = 120
ADMIN_PASSWORD = "WinAsOne"
DEV_PASSWORD = "WinAsOneDev"
WORKING_HOURS_START = 9
WORKING_HOURS_END = 17
CACHE_INTERVAL_MINUTES = 10
# DAYS_TO_SHOW_IMMEDIATELY = 3 # REMOVED: No longer needed

LANGUAGES = ["English", "German", "French", "Italian", "Spanish"]
TIMEZONE_OPTIONS = {
    "GMT / BST (London, Dublin)": "Europe/London",
    "CET (Paris, Berlin, Rome)": "Europe/Paris",
    "EET (Athens, Helsinki)": "Europe/Helsinki",
    "GST (Dubai, Abu Dhabi)": "Asia/Dubai",
}
DEFAULT_TIMEZONE_FRIENDLY = "GMT / BST (London, Dublin)"

# --- GLOBAL HELPERS ---
def format_to_iso_z(dt):
    """Formats a datetime object to the ISO Z format Calendly expects."""
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV string for downloading."""
    return df.to_csv(index=True).encode('utf-8')

def get_rounded_now(interval_minutes=CACHE_INTERVAL_MINUTES):
    """
    Rounds the current UTC time down to the nearest X-minute interval.
    This creates a stable time window for caching API calls.
    """
    now = datetime.now(pytz.UTC)
    minutes = (now.minute // interval_minutes) * interval_minutes
    return now.replace(minute=minutes, second=0, microsecond=0)

# --- CORE FUNCTIONS ---

def get_filtered_team_members():
    """Filters the hardcoded TEAM_DATA list."""
    return [
        m for m in TEAM_DATA
        if m["active"] and m["team"] == TEAM_TO_REPORT and m["userUri"] and m["soloEventUri"]
    ]

@st.cache_data(ttl=600) # Cache for 10 minutes (600 seconds)
def get_user_availability(solo_event_uri, start_date, end_date, api_key):
    """Fetches available slots from the Calendly API for a single user."""
    if not api_key: return []

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    all_slots = []
    base_url = "https://api.calendly.com/event_type_available_times"

    loop_start_date = start_date
    while loop_start_date < end_date:
        loop_end_date = loop_start_date + timedelta(days=7) # API limit is 7 days per request
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
        except requests.exceptions.HTTPError:
            pass
        loop_start_date += timedelta(days=7) # Move to next week
    return all_slots

@st.cache_data(ttl=3600)
def get_organization_uri(api_key):
    """Fetches the organization URI associated with the API key."""
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    url = "https://api.calendly.com/users/me"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("resource", {}).get("current_organization")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
             st.error("Invalid API Key. Please check your Streamlit secrets.", icon="🚨")
        else:
             st.error(f"Calendly API Error (User): {e.response.json().get('message', 'Unknown Error')}", icon="🚨")
        return None

@st.cache_data(ttl=600) # Cache for 10 minutes
def fetch_all_scheduled_events(organization_uri, start_date, end_date, api_key):
    """
    Fetches all booked appointments for an entire organization and
    returns a count of long events per user URI.
    """
    counts_by_user_uri = defaultdict(int)
    if not api_key or not organization_uri:
        return counts_by_user_uri

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    base_url = "https://api.calendly.com/scheduled_events"

    params = {
        'organization': organization_uri,
        'min_start_time': format_to_iso_z(start_date),
        'max_start_time': format_to_iso_z(end_date),
        'count': 100,
        'status': 'active'
    }

    while base_url:
        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            for event in data.get("collection", []):
                try:
                    start_str = event['start_time'].replace('Z', '+00:00')
                    end_str = event['end_time'].replace('Z', '+00:00')
                    start_time = datetime.fromisoformat(start_str)
                    end_time = datetime.fromisoformat(end_str)
                    duration_minutes = (end_time - start_time).total_seconds() / 60

                    if duration_minutes >= 60:
                        user_uri = event.get("event_memberships", [{}])[0].get("user")
                        if user_uri:
                            counts_by_user_uri[user_uri] += 1
                except Exception:
                    pass

            base_url = data.get("pagination", {}).get("next_page")
            params = {}

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                 st.error("API Key Error: This key does not have Organization-level permission to read scheduled events for all users. Please use an Admin-generated token.", icon="🚨")
            else:
                 st.error(f"Calendly API Error (Events): {e.response.json().get('message', 'Unknown Error')}", icon="🚨")
            base_url = None
        except Exception as e:
            st.error(f"A non-HTTP error occurred: {e}", icon="🚨")
            base_url = None

    return counts_by_user_uri

# --- THIS IS THE KEY FUNCTION FOR PERFORMANCE ---
@st.cache_data(ttl=600) # Cache for 10 minutes
def fetch_language_availability(team_members, api_key, selected_language, rounded_start_time):
    """
    Fetches availability for a single language using limited concurrency (8 workers)
    as a balance between desktop speed and mobile stability.
    The rounded_start_time parameter is the key to caching.
    """
    # Use the passed-in rounded time to define the search window
    minimum_booking_time = rounded_start_time + timedelta(hours=MINIMUM_NOTICE_HOURS)
    api_start_date = rounded_start_time + timedelta(minutes=1)
    # MODIFIED: Adjust end_date based on WORKING_DAYS_TO_CHECK
    api_end_date = api_start_date + timedelta(days=WORKING_DAYS_TO_CHECK + 4) # Add buffer for safety

    language_slots = []
    members_for_lang = [m for m in team_members if selected_language in m["languages"]]

    # --- Use ThreadPoolExecutor with max_workers=8 ---
    with ThreadPoolExecutor(max_workers=8) as executor:
        args = [(member, api_key) for member in members_for_lang]

        def fetch_availability(member, key):
            """Helper function to fetch slots and return the member info."""
            available_slots = get_user_availability(
                member["soloEventUri"], api_start_date, api_end_date, key
            )
            return member, available_slots

        results = executor.map(lambda p: fetch_availability(*p), args)

        for member, user_slots in results:
            for slot_time in user_slots:
                if slot_time >= minimum_booking_time:
                    language_slots.append({"specialist": member["name"], "dateTime": slot_time})

    language_slots.sort(key=lambda x: x["dateTime"])
    return language_slots

# --- THIS IS THE KEY FUNCTION FOR PERFORMANCE ---
@st.cache_data(ttl=600) # Cache for 10 minutes
def fetch_all_team_availability(team_members, api_key, rounded_start_time):
    """
    Fetches admin data. The rounded_start_time parameter is the key to caching.
    Uses full concurrency as it's less likely to be run on mobile.
    """
    # Use the passed-in rounded time to define the search window
    min_availability_time = rounded_start_time + timedelta(hours=MINIMUM_NOTICE_HOURS)
    api_availability_start = rounded_start_time + timedelta(minutes=1)
    # MODIFIED: Adjust end_date based on WORKING_DAYS_TO_CHECK
    api_availability_end = api_availability_start + timedelta(days=WORKING_DAYS_TO_CHECK + 4) # Add buffer for safety

    api_scheduled_start = rounded_start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    # MODIFIED: Adjust end_date based on WORKING_DAYS_TO_CHECK
    api_scheduled_end = api_scheduled_start + timedelta(days=WORKING_DAYS_TO_CHECK + 4) # Add buffer for safety

    availability_by_specialist = defaultdict(list)
    raw_slots_for_summary = []
    booked_event_counts = {}

    with ThreadPoolExecutor(max_workers=len(team_members) or 1) as executor:
        args = [(m, api_key) for m in team_members]
        def fetch_availability(member, key):
            available_slots = get_user_availability(
                member["soloEventUri"], api_availability_start, api_availability_end, key
            )
            return member, available_slots
        results = executor.map(lambda p: fetch_availability(*p), args)
        for member, user_slots in results:
            for slot_time in user_slots:
                if slot_time >= min_availability_time:
                    availability_by_specialist[member["name"]].append(slot_time)
                    raw_slots_for_summary.append({"specialist_info": member, "dateTime": slot_time})

    organization_uri = get_organization_uri(api_key)
    if organization_uri:
        counts_by_user_uri = fetch_all_scheduled_events(
            organization_uri, api_scheduled_start, api_scheduled_end, api_key
        )
        user_uri_to_name = {m['userUri']: m['name'] for m in team_members}
        for uri, count in counts_by_user_uri.items():
            if uri in user_uri_to_name:
                name = user_uri_to_name[uri]
                booked_event_counts[name] = count

    return availability_by_specialist, raw_slots_for_summary, booked_event_counts

@st.cache_data(ttl=3600) # Cache for 1 hour
def fetch_organization_discovery_report(organization_uri, api_key):
    """Fetches all users and their event types for an entire organization."""
    if not api_key or not organization_uri:
        return []

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    all_user_event_data = []

    users_url = f"https://api.calendly.com/organization_memberships?organization={organization_uri}&count=100"
    all_users = []

    while users_url:
        try:
            response = requests.get(users_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            all_users.extend(data.get("collection", []))
            users_url = data.get("pagination", {}).get("next_page")
        except requests.exceptions.HTTPError as e:
            st.error(f"Failed to fetch organization users: {e.response.json().get('message')}", icon="🚨")
            users_url = None

    for user_membership in all_users:
        user = user_membership.get("user", {})
        user_name = user.get("name")
        user_email = user.get("email")
        user_uri = user.get("uri")

        if not user_uri:
            continue

        events_url = f"https://api.calendly.com/event_types?user={user_uri}&count=50"

        while events_url:
            try:
                response = requests.get(events_url, headers=headers)
                response.raise_for_status()
                data = response.json()

                for event in data.get("collection", []):
                    if event.get("kind") == "solo":
                        all_user_event_data.append({
                            "User Name": user_name,
                            "User Email": user_email,
                            "User URI": user_uri,
                            "Event Type Name": event.get("name"),
                            "Event Type URI": event.get("uri"),
                            "Event Active": event.get("active", False)
                        })

                events_url = data.get("pagination", {}).get("next_page")
            except requests.exceptions.HTTPError:
                events_url = None

    return all_user_event_data

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
    """
    Gets the next N working days.
    MODIFIED: Starts from tomorrow.
    """
    days = []
    # Start from tomorrow in the specified timezone
    current_day = datetime.now(timezone).date() + timedelta(days=1)
    while len(days) < n:
        if current_day.weekday() < 5: # Monday = 0, Sunday = 6
            days.append(current_day)
        current_day += timedelta(days=1)
    return days

# --- UI HELPER FUNCTIONS ---
def display_main_availability(all_slots, language, timezone, timezone_friendly):
    """
    Renders the main availability view for a selected language.
    MODIFIED: Shows all available days directly (no expander).
    """
    if all_slots is None:
        return

    slots_by_day = defaultdict(list)
    # Use the globally configured WORKING_DAYS_TO_CHECK
    working_days = get_next_working_days(WORKING_DAYS_TO_CHECK, timezone)
    for slot in all_slots:
        day = slot["dateTime"].astimezone(timezone).date()
        if day in working_days:
            slots_by_day[day].append(slot)

    if not slots_by_day:
         st.info(f"No upcoming availability found for **{language}** in the next {WORKING_DAYS_TO_CHECK} working days.")
         return

    st.header(f"Available Slots for {language}")
    st.write(f"Times are shown in **{timezone_friendly}**.")
    st.divider()

    time_slot_style = (
        "display: inline-block; "
        "border: 1px solid #e0e0e0; "
        "border-radius: 5px; "
        "padding: 8px 12px; "
        "margin: 4px; "
        "font-weight: 500;"
    )

    # Function to render a single day
    def render_day(day, day_slots_for_render):
        st.subheader(day.strftime('%A, %d %B %Y'))
        unique_times = sorted(list(set(s['dateTime'].astimezone(timezone).strftime('%H:%M') for s in day_slots_for_render)))
        time_tags = "".join([f"<div style='{time_slot_style}'>🕒 {time_str}</div>" for time_str in unique_times])
        st.markdown(f"<div style='display: flex; flex-wrap: wrap;'>{time_tags}</div>", unsafe_allow_html=True)
        st.divider()

    # --- MODIFICATION: Render all available days directly ---
    for day in working_days:
        if day in slots_by_day:
            render_day(day, slots_by_day[day])
    # --- END MODIFICATION ---

    # Summary remains the same
    st.header("Summary of Daily Availability")
    summary_data = []
    # Use the ordered list of working_days to ensure summary table is chronological
    for day in working_days:
         if day in slots_by_day:
            day_slots_summary = slots_by_day[day]
            slots_by_specialist = defaultdict(list)
            for slot in day_slots_summary:
                slots_by_specialist[slot['specialist']].append(slot['dateTime'])
            total_true_slots = sum(calculate_true_slots(s_slots) for s_slots in slots_by_specialist.values())
            summary_data.append({"Date": day.strftime('%A, %d %B'), "Bookable Slots": total_true_slots})
    if summary_data:
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

# --- STREAMLIT UI ---

st.set_page_config(layout="wide")
st.title("EMEA Onboarding Team Availability")

# --- Initialize session state ---
if 'availability_data' not in st.session_state:
    st.session_state['availability_data'] = None
if 'last_params' not in st.session_state:
    st.session_state['last_params'] = {}
if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False
if 'dev_authenticated' not in st.session_state:
    st.session_state['dev_authenticated'] = False
if 'admin_data' not in st.session_state:
    st.session_state['admin_data'] = None
if 'org_report_data' not in st.session_state:
    st.session_state['org_report_data'] = None

team_members = get_filtered_team_members()
calendly_api_key = st.secrets.get("CALENDLY_API_KEY")

# --- MAIN PAGE CONTROLS (MOVED FROM SIDEBAR) ---
st.write("Select your language and timezone to find open slots.")

col1, col2 = st.columns([1, 1])
with col1:
    selected_language = st.selectbox("Select language", options=LANGUAGES, key="main_lang")
with col2:
    selected_timezone_friendly = st.selectbox(
        "Select your timezone",
        options=TIMEZONE_OPTIONS.keys(),
        index=list(TIMEZONE_OPTIONS.keys()).index(DEFAULT_TIMEZONE_FRIENDLY),
        key="main_tz"
    )

selected_timezone = pytz.timezone(TIMEZONE_OPTIONS[selected_timezone_friendly])

# --- Get Availability Button ---
if st.button("Get Availability", type="primary", use_container_width=True):
    st.session_state['availability_data'] = None # Force a refresh
    st.session_state['admin_data'] = None # Clear admin data
    st.session_state['org_report_data'] = None # Clear dev data

    if not team_members:
        st.warning(f"No active members found for the '{TEAM_TO_REPORT}' team.")
    else:
        with st.spinner(f"Fetching latest availability for {selected_language}..."):
            rounded_now = get_rounded_now()
            all_slots = fetch_language_availability(
                team_members, calendly_api_key, selected_language, rounded_now
            )
            st.session_state['availability_data'] = all_slots
            st.session_state['last_params'] = {'lang': selected_language, 'tz_friendly': selected_timezone_friendly}
else:
    # On first load, or if no button pressed, show instruction
    if st.session_state['availability_data'] is None:
        st.info("Click 'Get Availability' to see the latest slots.")

st.divider()

# --- Main Page Display ---
if st.session_state['availability_data'] is not None:
    last_params = st.session_state.get('last_params', {})
    lang_to_display = last_params.get('lang', selected_language)
    tz_friendly_to_display = last_params.get('tz_friendly', selected_timezone_friendly)
    tz_to_display = pytz.timezone(TIMEZONE_OPTIONS.get(tz_friendly_to_display, "Europe/London"))

    display_main_availability(
        st.session_state['availability_data'],
        lang_to_display,
        tz_to_display,
        tz_friendly_to_display
    )

# --- SIDEBAR: Admin & Dev Sections ---
st.sidebar.header("Admin Access")
password = st.sidebar.text_input("Enter password", type="password", key="admin_pass")

if st.sidebar.button("Unlock Admin View"):
    if password == ADMIN_PASSWORD:
        st.session_state['admin_authenticated'] = True
        st.session_state['dev_authenticated'] = False
        st.session_state['admin_data'] = None
        st.session_state['org_report_data'] = None
    else:
        st.sidebar.error("Incorrect password.", key="admin_err")
        st.session_state['admin_authenticated'] = False

st.sidebar.divider()
st.sidebar.header("Developer Access")
dev_password = st.sidebar.text_input("Enter developer password", type="password", key="dev_pass")

if st.sidebar.button("Unlock Developer Tools"):
    if dev_password == DEV_PASSWORD:
        st.session_state['dev_authenticated'] = True
        st.session_state['admin_authenticated'] = False
        st.session_state['admin_data'] = None
        st.session_state['org_report_data'] = None
    else:
        st.sidebar.error("Incorrect password.", key="dev_err")
        st.session_state['dev_authenticated'] = False


# --- MAIN PAGE - ADMIN VIEW ---
if st.session_state.get('admin_authenticated'):
    st.sidebar.success("Admin view unlocked!")
    st.divider()
    st.header("🔒 Admin View")

    # --- MODIFIED: Added a button to "lazy load" the admin data ---
    if st.button("Load Admin Reports", key="load_admin_data"):
        st.session_state['admin_data'] = None # Force a refresh
        with st.spinner("Fetching all team availability for admin view..."):
            active_team_members = get_filtered_team_members()
            rounded_now = get_rounded_now()
            admin_availability, raw_slots, booked_counts = fetch_all_team_availability(
                active_team_members,
                calendly_api_key,
                rounded_now
            )
            st.session_state['admin_data'] = (admin_availability, raw_slots, booked_counts)

    # This data display logic only runs if admin_data exists in session state
    if st.session_state['admin_data'] is None:
        st.info("Click 'Load Admin Reports' to fetch and display the admin dashboard.")
    else:
        admin_availability, raw_slots, booked_counts = st.session_state['admin_data']

        if not admin_availability and not booked_counts and not raw_slots:
            st.warning("No availability or booked events found for any team member.")
        else:
            active_team_members = get_filtered_team_members()
            # Use the default London timezone for consistent Admin reporting
            uk_timezone = pytz.timezone("Europe/London")
            # Use the globally configured WORKING_DAYS_TO_CHECK for Admin reports
            working_days = get_next_working_days(WORKING_DAYS_TO_CHECK, uk_timezone)

            # --- 1. Language Summary ---
            st.subheader("Team Summary by Language")
            st.write("Total bookable slots for the entire team.")
            st.info("💡 For the best experience, view these tables on a desktop computer.")

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

            def color_summary_cells(val):
                if val == 0: return 'background-color: #ffcccb; color: black;'
                elif 1 <= val <= 4: return 'background-color: #d4edda; color: black;'
                else: return 'background-color: #28a745; color: white;'

            st.dataframe(summary_df.style.applymap(color_summary_cells), use_container_width=True)
            st.download_button(
                 label="Download Language Summary as CSV",
                 data=convert_df_to_csv(summary_df),
                 file_name="language_summary.csv",
                 mime="text/csv",
             )
            st.divider()

            # --- 2. Team Capacity Heatmap ---
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
            heatmap_df.index.name = "Specialist"
            heatmap_df = heatmap_df.reindex(sorted(heatmap_df.index))

            def color_heatmap_cells(val):
                if val == 0: return 'background-color: #ffcccb; color: black;'
                elif 1 <= val <= 2: return 'background-color: #d4edda; color: black;'
                else: return 'background-color: #28a745; color: white;'

            st.dataframe(heatmap_df.style.applymap(color_heatmap_cells), use_container_width=True)
            st.download_button(
                 label="Download Heatmap as CSV",
                 data=convert_df_to_csv(heatmap_df),
                 file_name="team_capacity_heatmap.csv",
                 mime="text/csv",
             )
            st.divider()

            # --- 3. Booked Appointments Report ---
            st.subheader("Booked Appointments Report")
            st.write(f"Total count of booked appointments 60 minutes or longer in the next {WORKING_DAYS_TO_CHECK} working days.")

            report_data = []
            # Ensure all active members are in the report, even if they have 0 booked events
            specialist_names = sorted([m['name'] for m in active_team_members])

            for specialist in specialist_names:
                report_data.append({
                    "Specialist": specialist,
                    "Booked Appointments (60+ min)": booked_counts.get(specialist, 0) # Use .get with default 0
                })

            report_df = pd.DataFrame(report_data).set_index("Specialist")
            st.dataframe(report_df, use_container_width=True)
            st.download_button(
                 label="Download Booked Report as CSV",
                 data=convert_df_to_csv(report_df),
                 file_name="booked_appointments_report.csv",
                 mime="text/csv",
             )
            st.divider()

            # --- 4. Detailed Specialist Availability ---
            st.subheader("Detailed Specialist Availability")
            # Ensure all active members are listed, even if they have 0 available slots
            sorted_specialists = sorted([m['name'] for m in active_team_members])
            for specialist in sorted_specialists:
                 # Use .get with default empty list
                slots = admin_availability.get(specialist, [])
                with st.expander(f"**{specialist}** - {len(slots)} available slots found"):
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

                    # Iterate through the ordered working_days list
                    for day in working_days:
                         if day in slots_by_day:
                            st.markdown(f"**{day.strftime('%A, %d %B')}**")
                            day_slots = sorted(slots_by_day[day])
                            time_strings = [f"`{s.strftime('%H:%M')}`" for s in day_slots]
                            st.write(" | ".join(time_strings))

            st.divider()

# --- MAIN PAGE - DEV VIEW ---
if st.session_state.get('dev_authenticated'):
    st.sidebar.success("Developer tools unlocked!")
    st.divider()
    st.header("⚙️ Developer Tools")

    # --- Organization Discovery Tool ---
    st.subheader("Organization Discovery Tool")
    st.write("A tool to find all users and their 'solo' event types in your Calendly organization. Use this to find the URIs needed to build new team apps.")
    st.warning("This tool scans your *entire* organization and may be slow.")

    # --- MODIFIED: The button now only triggers the fetch ---
    if st.button("Run Organization Discovery Report"):
        st.session_state['org_report_data'] = None # Clear old data
        organization_uri = get_organization_uri(calendly_api_key)
        if organization_uri:
            with st.spinner("Scanning your organization... This may take a minute."):
                report_data = fetch_organization_discovery_report(organization_uri, calendly_api_key)
                if report_data:
                    df = pd.DataFrame(report_data)
                    st.session_state['org_report_data'] = df
                else:
                    st.error("Could not retrieve organization report.")
        else:
            st.error("Could not retrieve organization URI. Check API Key permissions.")

    # --- MODIFIED: Display logic is separate and checks session state ---
    if st.session_state['org_report_data'] is None:
        st.info("Click 'Run Organization Discovery Report' to fetch data.")
    else:
        df = st.session_state['org_report_data']
        st.dataframe(df, use_container_width=True)
        st.download_button(
            label="Download Full Report as CSV",
            data=convert_df_to_csv(df),
            file_name="full_organization_event_report.csv",
            mime="text/csv",
        )


import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz # Library for timezone handling
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor # For parallel API calls

# --- CONFIGURATION ---
# --- APAC TEAM DATA ---
TEAM_DATA = [
    {
        "name": "Anthony Ferlazzo",
        "userUri": "https://api.calendly.com/users/HCHECMCAGLZOSHN7",
        "soloEventUri": "https://api.calendly.com/event_types/GDEDPXPOOJEF32SR",
        "languages": ["English"],
        "team": "APAC",
        "active": True
    },
    {
        "name": "Gem Rooke",
        "userUri": "https://api.calendly.com/users/bfc287f8-5679-44c2-92bf-878d73a5a34d",
        "soloEventUri": "https://api.calendly.com/event_types/e8674269-3543-4d7a-9f86-df9e803ba3b6",
        "languages": ["English"],
        "team": "APAC",
        "active": True
    },
    {
        "name": "CP Kelleyen",
        "userUri": "https://api.calendly.com/users/ec1f3b31-8a31-4359-84f2-e0f8b6793b41",
        "soloEventUri": "https://api.calendly.com/event_types/8973b256-0761-4f8e-b250-7bced9ab0647",
        "languages": ["English"],
        "team": "APAC",
        "active": True
    },
    {
        "name": "Lip Rad",
        "userUri": "https://api.calendly.com/users/EFHAAIGCGF6Q6R3D",
        "soloEventUri": "https://api.calendly.com/event_types/FCACKUDXCA4M4DJ5",
        "languages": ["English"],
        "team": "APAC",
        "active": True
    },
]

# --- CONSTANTS (Copied from EMEA logic) ---
WORKING_DAYS_TO_CHECK = 10 
MINIMUM_NOTICE_HOURS = 21
SLOT_DURATION_MINUTES = 120
ADMIN_PASSWORD = "WinAsOne" # Kept from EMEA
DEV_PASSWORD = "WinAsOneDev" # Kept from EMEA
WORKING_HOURS_START = 9
WORKING_HOURS_END = 17

# --- APAC LANGUAGE & TIMEZONE CONFIG ---
LANGUAGES = ["English"] # Only English
TIMEZONE_OPTIONS = {
    "UTC+7 (Bangkok)": "Asia/Bangkok",
    "UTC+8 (Singapore/Manila/Perth)": "Asia/Singapore",
    "UTC+9:30 (Darwin)": "Australia/Darwin",
    "UTC+10 (Melbourne/Sydney/Brisbane)": "Australia/Melbourne",
    "UTC+12 (Auckland)": "Pacific/Auckland",
}
DEFAULT_TIMEZONE_FRIENDLY = "UTC+10 (Melbourne/Sydney/Brisbane)"

# --- GLOBAL HELPERS ---
def format_to_iso_z(dt):
    """Formats a datetime object to the ISO Z format Calendly expects."""
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV string for downloading."""
    return df.to_csv(index=True).encode('utf-8')

# --- CORE FUNCTIONS ---

def get_filtered_team_members():
    """Filters the hardcoded TEAM_DATA list for active APAC members."""
    # Modified from EMEA: No TEAM_TO_REPORT filter needed
    return [
        m for m in TEAM_DATA
        if m["active"] and m["userUri"] and m["soloEventUri"]
    ]

@st.cache_data(ttl=600)
def get_user_availability(solo_event_uri, start_date, end_date, api_key):
    """Fetches available slots from the Calendly API for a single user."""
    if not api_key: return []

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    all_slots = []
    base_url = "https://api.calendly.com/event_type_available_times"
    
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
        except requests.exceptions.HTTPError: 
            pass 
        loop_start_date += timedelta(days=7)
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

@st.cache_data(ttl=600)
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

def fetch_language_availability(team_members, api_key, selected_language):
    """Fetches availability for a single language using concurrent API calls for speed."""
    utc, now = pytz.UTC, datetime.now(pytz.UTC)
    minimum_booking_time = now + timedelta(hours=MINIMUM_NOTICE_HOURS)
    api_start_date = now + timedelta(minutes=1)
    api_end_date = api_start_date + timedelta(days=WORKING_DAYS_TO_CHECK + 4) 

    language_slots = []
    # Filter for language (will just be English, but keeps logic identical)
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
    """
    Fetches availability (concurrently) AND all scheduled events (one big call) 
    for all team members.
    """
    utc, now = pytz.UTC, datetime.now(pytz.UTC)
    
    min_availability_time = now + timedelta(hours=MINIMUM_NOTICE_HOURS)
    api_availability_start = now + timedelta(minutes=1)
    api_availability_end = api_availability_start + timedelta(days=WORKING_DAYS_TO_CHECK + 4)
    
    api_scheduled_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    api_scheduled_end = api_scheduled_start + timedelta(days=WORKING_DAYS_TO_CHECK + 4) 
    
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

# --- Function for Organization Discovery (from EMEA) ---
@st.cache_data(ttl=3600) # Cache for 1 hour
def fetch_organization_discovery_report(organization_uri, api_key):
    """Fetches all users and their event types for an entire organization."""
    if not api_key or not organization_uri:
        return []
    
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    all_user_event_data = []

    # 1. Get all users in the organization
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
    
    # 2. For each user, get their event types
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
                    # Only include solo events
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
                events_url = None # Silently fail for one user's events

    return all_user_event_data

# --- NEW: Function for Single User Event Discovery ---
@st.cache_data(ttl=60) # Cache for 1 minute
def fetch_user_event_types(user_uri, api_key):
    """Fetches all 'solo' event types for a single user URI."""
    if not api_key or not user_uri:
        return []
    
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    events_url = f"https://api.calendly.com/event_types?user={user_uri}&count=50"
    user_events = []
    
    while events_url:
        try:
            response = requests.get(events_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            for event in data.get("collection", []):
                # Only include solo events
                if event.get("kind") == "solo":
                    user_events.append({
                        "Event Type Name": event.get("name"),
                        "Event Type URI": event.get("uri"),
                        "Event Active": event.get("active", False)
                    })
            
            events_url = data.get("pagination", {}).get("next_page")
        except requests.exceptions.HTTPError as e:
            st.error(f"Failed to fetch events for user: {e.response.json().get('message')}", icon="🚨")
            events_url = None # Stop on error

    return user_events

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

# --- UI HELPER FUNCTIONS ---
def display_main_availability(all_slots, language, timezone, timezone_friendly):
    """Renders the main availability view for a selected language."""
    if all_slots is None:
        return 

    slots_by_day = defaultdict(list)
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

    for day in working_days:
        if day in slots_by_day:
            st.subheader(day.strftime('%A, %d %B %Y'))
            day_slots = slots_by_day[day]
            unique_times = sorted(list(set(s['dateTime'].astimezone(timezone).strftime('%H:%M') for s in day_slots)))
            
            time_tags = "".join([f"<div style='{time_slot_style}'>🕒 {time_str}</div>" for time_str in unique_times])
            st.markdown(f"<div style='display: flex; flex-wrap: wrap;'>{time_tags}</div>", unsafe_allow_html=True)
            
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

# --- STREAMLIT UI ---

st.set_page_config(layout="wide")
st.title("🌏 APAC Availability") # <-- UPDATED TITLE

if 'last_params' not in st.session_state:
    st.session_state['last_params'] = {}
if 'availability_data' not in st.session_state:
    st.session_state['availability_data'] = None
if 'admin_authenticated' not in st.session_state: 
    st.session_state['admin_authenticated'] = False
if 'dev_authenticated' not in st.session_state:
    st.session_state['dev_authenticated'] = False
if 'admin_data' not in st.session_state: 
    st.session_state['admin_data'] = None
if 'org_report_data' not in st.session_state:
    st.session_state['org_report_data'] = None
if 'user_report_data' not in st.session_state: # <-- NEW
    st.session_state['user_report_data'] = None


# --- Sidebar ---
st.sidebar.header("Options")
# --- LANGUAGE FILTER REMOVED ---
selected_language = "English" # Hardcoded to English
# st.sidebar.selectbox("Select language", options=LANGUAGES) # <-- REMOVED

selected_timezone_friendly = st.sidebar.selectbox(
    "Select your timezone", 
    options=TIMEZONE_OPTIONS.keys(), 
    index=list(TIMEZONE_OPTIONS.keys()).index(DEFAULT_TIMEZONE_FRIENDLY)
)
selected_timezone = pytz.timezone(TIMEZONE_OPTIONS[selected_timezone_friendly])

team_members = get_filtered_team_members()
calendly_api_key = st.secrets.get("CALENDLY_API_KEY")

current_params = {'lang': selected_language, 'tz': selected_timezone_friendly}
if current_params != st.session_state.get('last_params'):
    st.session_state['availability_data'] = None 
    st.session_state['admin_data'] = None 
    st.session_state['org_report_data'] = None # Clear all data on param change
    st.session_state['user_report_data'] = None # <-- NEW

if st.session_state['availability_data'] is None:
    if not team_members:
        st.warning("No active members found for the APAC team.") # <-- Updated text
    else:
        with st.spinner(f"Fetching latest availability for {selected_language}..."):
            all_slots = fetch_language_availability(team_members, calendly_api_key, selected_language)
            st.session_state['availability_data'] = all_slots
            st.session_state['last_params'] = current_params

display_main_availability(st.session_state['availability_data'], selected_language, selected_timezone, selected_timezone_friendly)

# --- Admin Section ---
st.sidebar.divider()
st.sidebar.header("Admin Access")
password = st.sidebar.text_input("Enter password", type="password", key="admin_pass")

if st.sidebar.button("Unlock Admin View"):
    if password == ADMIN_PASSWORD:
        st.session_state['admin_authenticated'] = True
        st.session_state['dev_authenticated'] = False # Log out of dev
        st.session_state['admin_data'] = None 
        st.session_state['org_report_data'] = None 
        st.session_state['user_report_data'] = None # <-- NEW
    else:
        st.sidebar.error("Incorrect password.", key="admin_err")
        st.session_state['admin_authenticated'] = False

# --- Developer Section ---
st.sidebar.divider()
st.sidebar.header("Developer Access")
dev_password = st.sidebar.text_input("Enter developer password", type="password", key="dev_pass")

if st.sidebar.button("Unlock Developer Tools"):
    if dev_password == DEV_PASSWORD:
        st.session_state['dev_authenticated'] = True
        st.session_state['admin_authenticated'] = False # Log out of admin
        st.session_state['admin_data'] = None
        st.session_state['org_report_data'] = None
        st.session_state['user_report_data'] = None # <-- NEW
    else:
        st.sidebar.error("Incorrect developer password.", key="dev_err")
        st.session_state['dev_authenticated'] = False


# --- MAIN PAGE - ADMIN VIEW ---
if st.session_state.get('admin_authenticated'):
    st.sidebar.success("Admin view unlocked!")
    st.divider()
    st.header("🔒 Admin View")

    if st.session_state['admin_data'] is None:
        with st.spinner("Fetching all team availability for admin view..."):
            active_team_members = get_filtered_team_members()
            admin_availability, raw_slots, booked_counts = fetch_all_team_availability(
                active_team_members, 
                calendly_api_key
            )
            st.session_state['admin_data'] = (admin_availability, raw_slots, booked_counts)
    
    if st.session_state['admin_data'] is None:
        st.error("Failed to load admin data. Check API key and permissions.")
    else:
        admin_availability, raw_slots, booked_counts = st.session_state['admin_data']
    
        if not admin_availability and not booked_counts:
            st.warning("No availability or booked events found for any team member.")
        else:
            active_team_members = get_filtered_team_members()
            # Use the selected timezone for Admin view, not just UK
            admin_timezone = selected_timezone
            working_days = get_next_working_days(WORKING_DAYS_TO_CHECK, admin_timezone)
            
            # --- 1. Language Summary ---
            st.subheader("Team Summary by Language")
            st.write("Total bookable slots for the entire team.")
            st.info("💡 For the best experience, view these tables on a desktop computer.")
            
            lang_summary_slots = defaultdict(lambda: defaultdict(int))
            slots_by_specialist_day = defaultdict(lambda: defaultdict(list))

            for slot in raw_slots:
                day = slot['dateTime'].astimezone(admin_timezone).date() # Use admin_timezone
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
            for lang in LANGUAGES: # This will just be "English"
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
                    day = slot_time.astimezone(admin_timezone).date() # Use admin_timezone
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
            specialist_names = sorted([m['name'] for m in active_team_members])
            
            for specialist in specialist_names:
                report_data.append({
                    "Specialist": specialist, 
                    "Booked Appointments (60+ min)": booked_counts.get(specialist, 0)
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
            sorted_specialists = sorted(admin_availability.keys())
            for specialist in sorted_specialists:
                with st.expander(f"**{specialist}** - {len(admin_availability.get(specialist, []))} available slots found"):
                    slots = admin_availability.get(specialist)
                    if not slots:
                        st.write("No availability in the upcoming period.")
                        continue
                    slots_by_day = defaultdict(list)
                    for slot_time_utc in slots:
                        day = slot_time_utc.astimezone(admin_timezone).date() # Use admin_timezone
                        if day in working_days:
                            slots_by_day[day].append(slot_time_utc.astimezone(admin_timezone)) # Use admin_timezone
                    
                    if not slots_by_day:
                        st.write("No availability on upcoming weekdays.")
                        continue

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

    # --- NEW: Single User Tool ---
    st.divider()
    st.subheader("Single User Event-Type Discovery (Fast)")
    st.write("Fetch all 'solo' event types for one specific user URI.")
    
    # Pre-fill with Anthony's URI as a helper
    default_user_uri = TEAM_DATA[0].get('userUri', '') 
    user_uri_to_check = st.text_input("User URI to check", value=default_user_uri)
    
    if st.button("Fetch Events for User"):
        st.session_state['user_report_data'] = None # Clear old
        if user_uri_to_check:
            with st.spinner(f"Fetching events for {user_uri_to_check}..."):
                report_data = fetch_user_event_types(user_uri_to_check, calendly_api_key)
                if report_data:
                    df = pd.DataFrame(report_data)
                    st.session_state['user_report_data'] = df
                else:
                    st.error("No 'solo' events found for this user.")
        else:
            st.warning("Please enter a User URI.")
    
    if st.session_state['user_report_data'] is not None:
        st.dataframe(st.session_state['user_report_data'], use_container_width=True)

    # --- Original Organization Discovery Tool ---
    st.divider()
    st.subheader("Organization Discovery Tool (Slow)")
    st.write("A tool to find all users and their 'solo' event types in your Calendly organization. Use this to find the URIs needed to build new team apps.")
    st.warning("This tool scans your *entire* organization and may be slow.")
    
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

    if st.session_state['org_report_data'] is not None:
        df = st.session_state['org_report_data']
        st.dataframe(df, use_container_width=True)
        st.download_button(
            label="Download Full Report as CSV",
            data=convert_df_to_csv(df),
            file_name="full_organization_event_report.csv",
            mime="text/csv",
        )


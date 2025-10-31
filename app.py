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
        "name": "Anthony Ferlazzo",
        "userUri": "https://api.calendly.com/users/HCHECMCAGLZOSHN7",
        "soloEventUri": "https://api.calendly.com/event_types/ECB2NPVJCAKUXGR7",
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

# Supported languages for filtering
SUPPORTED_LANGUAGES = ["English"]

# Timezone configuration
# Map display strings to a primary IANA timezone for that group.
# The primary timezone will be used for calculations.
TIMEZONE_MAP = {
    "UTC+7 (Bangkok)": "Asia/Bangkok",
    "UTC+8 (Singapore/Manila/Perth)": "Asia/Singapore",
    "UTC+9:30 (Darwin)": "Australia/Darwin",
    "UTC+10 (Melbourne/Sydney/Brisbane)": "Australia/Melbourne",
    "UTC+12 (Auckland)": "Pacific/Auckland",
}

# The list of options to show in the dropdown
TIMEZONES_DISPLAY = list(TIMEZONE_MAP.keys())
# The default display string
DEFAULT_TIMEZONE_DISPLAY = "UTC+10 (Melbourne/Sydney/Brisbane)"

# Check if default is valid, otherwise use first
if DEFAULT_TIMEZONE_DISPLAY in TIMEZONES_DISPLAY:
    default_tz_index = TIMEZONES_DISPLAY.index(DEFAULT_TIMEZONE_DISPLAY)
else:
    default_tz_index = 0

# Other constants
DAYS_TO_SHOW = 14 # Show availability for the next 14 days
MAX_WORKERS = 10 # Number of parallel threads to fetch data

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="APAC Availability",
    page_icon="🌏",
    layout="wide"
)

# --- STATE MANAGEMENT ---
# Initialize session state variables
if 'availability_data' not in st.session_state:
    st.session_state['availability_data'] = None
if 'last_run_params' not in st.session_state:
    st.session_state['last_run_params'] = None
if 'org_report_data' not in st.session_state:
    st.session_state['org_report_data'] = None

# --- API FUNCTIONS ---

@st.cache_data(ttl=600) # Cache data for 10 minutes
def get_availability(user_uri, event_type_uri, start_time_str, end_time_str, api_key):
    """
    Fetches availability for a specific user and event type from Calendly.
    """
    url = "https://api.calendly.com/event_type_available_times"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "event_type": event_type_uri,
        "start_time": start_time_str,
        "end_time": end_time_str
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data.get("collection", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching availability for {user_uri}: {e}")
        return []

def get_availability_for_user(user, start_date, end_date, selected_timezone, api_key):
    """
    Wrapper function to fetch availability for one user, formatted for ThreadPoolExecutor.
    """
    if not user["active"] or not user["soloEventUri"]:
        return user["name"], user["languages"], []

    # Format dates for API call (must be in UTC)
    start_time_utc = selected_timezone.localize(datetime.combine(start_date, datetime.min.time())).astimezone(pytz.utc)
    end_time_utc = selected_timezone.localize(datetime.combine(end_date, datetime.max.time())).astimezone(pytz.utc)
    
    start_time_str = start_time_utc.isoformat().replace('+00:00', 'Z')
    end_time_str = end_time_utc.isoformat().replace('+00:00', 'Z')

    availability_slots = get_availability(user["userUri"], user["soloEventUri"], start_time_str, end_time_str, api_key)
    
    return user["name"], user["languages"], availability_slots

def process_availability_data(all_availability, selected_timezone, start_date, end_date):
    """
    Processes the raw availability data into a structured format for display.
    """
    daily_availability = defaultdict(lambda: defaultdict(list))
    
    for user_name, languages, slots in all_availability:
        if not slots:
            continue
            
        for slot in slots:
            start_time_utc = datetime.fromisoformat(slot["start_time"].replace("Z", "+00:00"))
            start_time_local = start_time_utc.astimezone(selected_timezone)
            
            date_str = start_time_local.strftime("%Y-%m-%d")
            time_str = start_time_local.strftime("%I:%M %p") # 12-hour format
            
            daily_availability[date_str][user_name].append(time_str)

    # Create a list of dates to iterate over
    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    
    processed_data = []
    for date in date_range:
        date_str = date.strftime("%Y-%m-%d")
        day_name = date.strftime("%A") # Get day of the week
        
        # Check for weekend
        is_weekend = day_name in ["Saturday", "Sunday"]
        
        row = {"Date": date.strftime("%Y-%m-%d (%A)")}
        
        # Check if the date has any availability data at all
        if date_str not in daily_availability and is_weekend:
            # Weekend with no slots, mark all active users as "Weekend"
            for user in TEAM_DATA:
                if user["active"]:
                    row[user["name"]] = "Weekend"
        elif date_str not in daily_availability:
            # Weekday with no slots, mark all active users as "No Availability"
            for user in TEAM_DATA:
                if user["active"]:
                    row[user["name"]] = "No Availability"
        else:
            # Date has availability, fill it in
            slots_for_day = daily_availability[date_str]
            for user in TEAM_DATA:
                if not user["active"]:
                    row[user["name"]] = "Inactive"
                elif user["name"] in slots_for_day:
                    # Join slots with a comma
                    row[user["name"]] = ", ".join(slots_for_day[user["name"]])
                elif is_weekend:
                    # Weekend, but no slots found (unlikely but safe)
                    row[user["name"]] = "Weekend"
                else:
                    # Weekday, but no slots for this specific user
                    row[user["name"]] = "No Availability"
                    
        processed_data.append(row)
        
    return pd.DataFrame(processed_data)

def convert_df_to_csv(df):
    """Converts DataFrame to CSV string for downloading."""
    return df.to_csv(index=False).encode('utf-8')

# --- UI LAYOUT ---

st.title("🌏 APAC Availability")

# Get Calendly API Key
calendly_api_key = st.secrets.get("CALENDLY_API_KEY")
if not calendly_api_key:
    st.error("CALENDLY_API_KEY secret not found. Please add it to your Streamlit secrets.")
    st.stop()

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Filters")
    
    # Date range selection
    st.subheader("Date Range")
    today = datetime.now().date()
    start_date = st.date_input("Start Date", today)
    end_date = st.date_input("End Date", today + timedelta(days=DAYS_TO_SHOW))

    if start_date > end_date:
        st.warning("End date must be after start date.")
    
    st.divider()
    
    # Timezone selection
    st.subheader("Timezone")
    selected_timezone_display_str = st.selectbox(
        "Select Timezone",
        TIMEZONES_DISPLAY,
        index=default_tz_index
    )
    # Get the actual IANA timezone name from the display string
    selected_timezone_str = TIMEZONE_MAP[selected_timezone_display_str]
    selected_timezone = pytz.timezone(selected_timezone_str)
    
    st.divider()

    # Language filter
    st.subheader("Language")
    selected_language = st.selectbox(
        "Filter by Language",
        ["All"] + SUPPORTED_LANGUAGES
    )
    
    st.divider()

    # Get Availability Button
    if st.button("Get Availability", type="primary", use_container_width=True):
        # Set parameters for checking cache
        current_run_params = (start_date, end_date, selected_timezone_str, selected_language)
        
        # Check if we need to re-fetch
        if st.session_state['availability_data'] is None or current_run_params != st.session_state['last_run_params']:
            st.session_state['last_run_params'] = current_run_params
            st.session_state['availability_data'] = None # Clear old data
            
            # Filter users based on language
            if selected_language == "All":
                users_to_fetch = [user for user in TEAM_DATA if user["active"]]
            else:
                users_to_fetch = [
                    user for user in TEAM_DATA 
                    if user["active"] and selected_language in user["languages"]
                ]

            if not users_to_fetch:
                st.warning("No active team members match the selected language.")
            else:
                with st.spinner(f"Fetching availability for {len(users_to_fetch)} team member(s)..."):
                    all_availability = []
                    # Use ThreadPoolExecutor to fetch in parallel
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        futures = [
                            executor.submit(get_availability_for_user, user, start_date, end_date, selected_timezone, calendly_api_key)
                            for user in users_to_fetch
                        ]
                        for future in futures:
                            all_availability.append(future.result())

                    # Process and store the data
                    df = process_availability_data(all_availability, selected_timezone, start_date, end_date)
                    st.session_state['availability_data'] = df

# --- Main Page Display ---

if st.session_state['availability_data'] is None:
    st.info("Please select your filters in the sidebar and click 'Get Availability'.")
else:
    df = st.session_state['availability_data']
    
    # Filter DataFrame columns based on language selection
    if selected_language == "All":
        active_users = [user["name"] for user in TEAM_DATA if user["active"]]
        cols_to_show = ["Date"] + [user for user in active_users if user in df.columns]
    else:
        active_users = [
            user["name"] for user in TEAM_DATA 
            if user["active"] and selected_language in user["languages"]
        ]
        cols_to_show = ["Date"] + [user for user in active_users if user in df.columns]

    # Ensure 'Date' is always the first column and exists
    if "Date" not in df.columns:
        st.error("An error occurred: 'Date' column is missing.")
    else:
        # Reorder columns to ensure 'Date' is first, followed by filtered users
        missing_users = [user for user in active_users if user not in df.columns]
        if missing_users:
            st.warning(f"Data for {', '.join(missing_users)} could not be fetched. They may be inactive or have no 'solo' event URI set.")
        
        final_df = df[cols_to_show]

        st.divider()
        st.subheader(f"Availability from {start_date.strftime('%B %d')} to {end_date.strftime('%B %d')}")
        st.caption(f"All times are displayed in **{selected_timezone_display_str}** timezone.")

        # Display the DataFrame as a table
        st.dataframe(final_df, use_container_width=True)
        
        # Download button
        st.download_button(
            label="Download as CSV",
            data=convert_df_to_csv(final_df),
            file_name=f"apac_availability_{start_date}_to_{end_date}.csv",
            mime="text/csv",
        )


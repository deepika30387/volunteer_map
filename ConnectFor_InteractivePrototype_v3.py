#!/usr/bin/env python
# coding: utf-8

# In[6]:


import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from geopy.geocoders import OpenCage
from geopy.distance import geodesic
import ast
import datetime


# In[16]:


# 1. UI Setup
st.set_page_config(layout="wide", page_title="Volunteer Match")
st.title("Find Volunteering Near You")

OPENCAGE_API_KEY = "86bceaa9973847e5a1032dd0b43a4b4f"

def parse_causes(val):
    if pd.isna(val):
        return []
    val = str(val).strip()
    # If stored like "['Education', 'Environment']"
    if val.startswith('[') and val.endswith(']'):
        try:
            return [str(c).strip() for c in ast.literal_eval(val)]
        except Exception:
            pass
    # If stored like "Education, Environment"
    return [c.strip() for c in val.split(',') if c.strip()]

# 2. Load the data (Cache it so it doesn't reload on every click)
@st.cache_data
def load_data():
    df = pd.read_csv("onsite_connectfor_opportunities_mapped.csv").dropna(subset=['latitude', 'longitude'])
    df['parsed_causes'] = df['causesArea'].apply(parse_causes)

    # Parse dates
    df['start_date'] = pd.to_datetime(df['startDate'], errors='coerce')
    df['end_date'] = pd.to_datetime(df['endDate'], errors='coerce')

    # If a one-day event doesn't have an end date listed, default it to the start date
    df['end_date'] = df['end_date'].fillna(df['start_date'])

    return df

df = load_data()

# Extract all unique causes across all rows for the filter dropdown
all_causes = sorted(list({cause for sublist in df['parsed_causes'] for cause in sublist}))

# 3. Volunteer Input (The Sidebar)

st.sidebar.header("Filter Opportunities")

selected_causes = st.sidebar.multiselect(
    "Select Causes:",
    options=all_causes,
    default=[]  # Empty by default = show all causes
)

# Location & Radius Inputs
st.sidebar.subheader("Your Location")
user_location = st.sidebar.text_input("Enter city or neighborhood (e.g., Bandra, Mumbai)")
search_radius_km = st.sidebar.slider("Search Radius (km)", min_value=1, max_value=50, value=10)

# Time filters:
st.sidebar.subheader("When are you available?")

# Set default range from today to 30 days out
today = datetime.date.today()
default_end = today + datetime.timedelta(days=30)

# The widget returns a tuple of either 1 or 2 dates
selected_dates = st.sidebar.date_input(
    "Select Date Range",
    value=(today, default_end),
    min_value=today # Prevents users from searching in the past
)

# Apply the filter only when the user has clicked both a start and end date
if len(selected_dates) == 2:
    user_start, user_end = selected_dates

    # Convert Streamlit dates to pandas datetimes for comparison
    user_start_dt = pd.to_datetime(user_start)
    user_end_dt = pd.to_datetime(user_end)

    # The Overlap Logic: 
    # An event is visible if it starts before the user's window ends, 
    # AND ends after the user's window begins.
    df = df[
        (df['start_date'] <= user_end_dt) & 
        (df['end_date'] >= user_start_dt)
    ]
elif len(selected_dates) == 1:
    # Gentle nudge if they only clicked the start date on the calendar so far
    st.sidebar.info("Please select an end date on the calendar.")


# Filter by Cause first
if selected_causes:
    # Keep row if any of the opportunity's causes match the selection
    df = df[df['parsed_causes'].apply(lambda causes: any(c in selected_causes for c in causes))]



# 4. Map Setup
m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
cluster = MarkerCluster().add_to(m)

# 5. Geocode Volunteer & Apply Distance Filter
if user_location:
    geolocator = OpenCage(api_key=OPENCAGE_API_KEY)
    user_coords = geolocator.geocode(f"{user_location}, India")

    if user_coords:
        vol_lat, vol_lon = user_coords.latitude, user_coords.longitude

        # Add Volunteer Marker
        folium.Marker(
            [vol_lat, vol_lon], 
            icon=folium.Icon(color='green', icon='user'),
            popup="You are here"
        ).add_to(m)

        # Add Radius Circle
        folium.Circle(
            location=[vol_lat, vol_lon],
            radius=search_radius_km * 1000,
            color="blue",
            fill=True,
            fill_opacity=0.1
        ).add_to(m)

        # Dynamic Bounding Box for Auto-Zoom
        north = geodesic(kilometers=search_radius_km).destination((vol_lat, vol_lon), 0).latitude
        east = geodesic(kilometers=search_radius_km).destination((vol_lat, vol_lon), 90).longitude
        south = geodesic(kilometers=search_radius_km).destination((vol_lat, vol_lon), 180).latitude
        west = geodesic(kilometers=search_radius_km).destination((vol_lat, vol_lon), 270).longitude
        m.fit_bounds([[south, west], [north, east]])

        # Calculate distance
        df['distance_km'] = df.apply(
            lambda row: geodesic((vol_lat, vol_lon), (row['latitude'], row['longitude'])).km, 
            axis=1
        )
        df = df[df['distance_km'] <= search_radius_km]

        st.sidebar.success(f"Showing {len(df)} matching opportunities within {search_radius_km} km")
    else:
        st.sidebar.error("Location not found. Try adding a city name.")

# 6. Populate Pins on the Map
# 6. Populate Pins on the Map
for idx, row in df.iterrows():

    # --- Date Formatting Logic ---
    date_display = "Flexible / Ongoing" # Fallback if dates are missing

    # Check if we have valid datetime objects for this row
    if pd.notna(row.get('start_date')) and pd.notna(row.get('end_date')):
        # Format the dates as '15 Oct 2026'
        start_str = row['start_date'].strftime('%d %b %Y')
        end_str = row['end_date'].strftime('%d %b %Y')

        # Smart display: One-day vs Multi-day
        if start_str == end_str:
            date_display = f"{start_str} (One-day)"
        else:
            date_display = f"{start_str} to {end_str}"
    # -----------------------------------

    # Format causes
    causes_str = ", ".join(row['parsed_causes']) if row.get('parsed_causes') else "General"

    # --- Get the precision value safely ---
    precision_val = row.get('precision', 'Unknown')

    # Build the HTML popup, now including the date_display variable
    popup_html = f"""
    <div style="font-family: sans-serif; font-size: 13px; min-width: 200px;">
        <h4 style="margin: 0 0 5px 0; color: #1a73e8;">{row['ngoName']}</h4>
        <p style="margin: 2px 0;"><b>Opportunity:</b> {row.get('eventName')}</p>
        <p style="margin: 2px 0;"><b>When:</b> {date_display}</p>
        <p style="margin: 2px 0;"><b>Cause:</b> <span style="background-color: #f1f3f4; padding: 2px 6px; border-radius: 4px;">{causes_str}</span></p>
        <p style="margin: 2px 0 10px 0;"><b>City:</b> {row['onsiteCity']}</p>
        <p style="margin: 2px 0 10px 0; font-size: 11px; color: #6c757d;"><i>Geocoding: {precision_val}</i></p>


        <a href="mailto:contact@{str(row['ngoName']).replace(' ', '').lower()}.org?subject=Volunteering for {row.get('opportunity', 'Opportunity')}" 
           target="_blank" style="background-color: #28a745; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; display: block; text-align: center; margin-top: 5px;">
           Connect
        </a>
    </div>
    """

    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=folium.Popup(popup_html, max_width=320),
        tooltip=f"{row['ngoName']} - {causes_str}",
        icon=folium.Icon(color='red', icon='heart')
    ).add_to(cluster)

# 7. Layout Display
col1, col2 = st.columns([2, 1])

with col1:
    st_folium(
        m, 
        width=800, 
        height=550, 
        returned_objects=[], 
        key=f"map_{user_location}_{search_radius_km}_{'-'.join(selected_causes)}"
    )

with col2:
    st.markdown("### Matching Opportunities")
    display_cols = ['ngoName', 'eventName', 'onsiteCity','causesArea']

    st.dataframe(df[display_cols], width='stretch', hide_index=True)


# In[ ]:





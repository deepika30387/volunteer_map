#!/usr/bin/env python
# coding: utf-8

# In[8]:


import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from geopy.distance import geodesic
import ast
import datetime
from geopy.geocoders import ArcGIS
import urllib


# In[ ]:


# 1. PAGE SETUP
st.set_page_config(layout="wide", page_title="India NGOs")

# Global CSS Hack to fix white space and apply premium typography
st.markdown("""
<style>
    /* Force Streamlit to remove the massive top padding */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 0rem !important;
    }

    /* Sophisticated Title Styling */
    .premium-title {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-weight: 700;
        font-size: 2.8rem;
        color: #1e293b; /* Deep premium slate / charcoal */
        margin-top: 0;
        margin-bottom: 5px;
        letter-spacing: -0.5px;
    }

    .premium-subtitle {
        color: #64748b; /* Soft slate gray */
        font-size: 1.1rem;
        font-weight: 400;
        margin-top: 0;
        margin-bottom: 20px; /* Reduced bottom margin to pull map higher */
    }
</style>

<div style="text-align: center;">
    <h1 class="premium-title">Find NGOs Near You<span style="color: #1a73e8;">.</span></h1>
    <p class="premium-subtitle">Discover local organizations and volunteer opportunities across India.</p>
</div>
""", unsafe_allow_html=True)

# 2. Location & Radius Inputs
st.sidebar.subheader("Your Location")
user_location = st.sidebar.text_input("Enter city or neighborhood (e.g., Bandra, Mumbai)")
search_radius_km = st.sidebar.slider("Search Radius (km)", min_value=1, max_value=50, value=10)

@st.cache_data
def load_data():
    df = pd.read_csv("guidestar_ngos_database_clean.csv").dropna(subset=['latitude', 'longitude'])   
    return df

df = load_data()


# 4. Map Setup
m = folium.Map(
    location=[20.5937, 78.9629], 
    zoom_start=5,
    max_zoom=17,  # This entirely prevents the gray screen error!
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    attr='Tiles &copy; Esri'
)

cluster = MarkerCluster().add_to(m)

# 5. Geocode Volunteer & Apply Distance Filter

if user_location:

    geolocator = ArcGIS(user_agent="ngo_map_prototype")
    user_coords = geolocator.geocode(f"{user_location}, India")

    if user_coords:
        vol_lat, vol_lon = user_coords.latitude, user_coords.longitude

        # Add the translucent search radius circle

        folium.Circle(
            location=[vol_lat, vol_lon],
            radius=search_radius_km * 1000,  # Convert your slider's km into meters
            color="#28a745",                 # Match the green user pin
            fill=True,
            fill_color="#28a745",
            fill_opacity=0.1,                # 10% opacity for a soft, translucent look
            weight=1                         # Thin, clean outer border
        ).add_to(m)


        # Add Volunteer Marker (User's searched location)
        folium.CircleMarker(
            location=[vol_lat, vol_lon],
            radius=12,             # Slightly larger than the NGO pins (which are 8)
            popup=folium.Popup("<div style='font-family: sans-serif; text-align: center;'><b>📍 You are here</b></div>", max_width=150),
            color="#ffffff",       # Crisp white border
            fill=True,
            fill_color="#28a745",  # Solid green fill
            fill_opacity=1.0,      # 100% solid so it doesn't look transparent
            weight=3               # Thicker border line
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

        #st.sidebar.success(f"Showing {len(df)} matching NGOs within {search_radius_km} km")
    else:
        st.sidebar.error("Location not found. Try adding a city name.")


# 6. Populate Pins on the Map
for idx, row in df.iterrows():

    # URL-encode the specific NGO name for the error form
    safe_ngo = urllib.parse.quote(str(row['NGO_name']))
    error_url = f"https://docs.google.com/forms/d/e/1FAIpQLSdpVdoglgsxpPL8bageLbA260GFMPYz1llkju29ewmUqo9xNg/viewform?usp=pp_url&entry.2094537900={safe_ngo}"

    # NEW: Generate the Google Maps Search URL using the exact coordinates
    gmaps_url = f"https://www.google.com/maps/search/?api=1&query={row['latitude']},{row['longitude']}"

    # Build the HTML popup with the new Google Maps button
    popup_html = f"""
    <div style="font-family: sans-serif; font-size: 13px; min-width: 200px;">
        <h4 style="margin: 0 0 5px 0; color: #1a73e8;">{row['NGO_name']}</h4>
        <p style="margin: 2px 0;"><b>Contact:</b> {row.get('Contact')}</p>
        <p style="margin: 2px 0;"><b>Phone:</b> {row.get('Contact_no')}</p>
        <p style="margin: 2px 0 10px 0;"><b>Address:</b> {row['Address']}</p>

        <!-- Google Maps Button (Styled in Google Blue) -->
        <a href="{gmaps_url}" target="_blank" style="background-color: #4285F4; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; display: block; text-align: center; margin-top: 10px; font-weight: bold;">
            📍 Open in Google Maps
        </a>

        <hr style="margin: 12px 0 8px 0; border: 0; border-top: 1px solid #eee;">
        <a href="{error_url}" target="_blank" style="color: #d9534f; font-size: 11px; text-decoration: none;">
            Report an error with this listing
        </a>
    </div>
    """

    # Use CircleMarker instead (notice there is no 'icon=' line here)
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=8,
        popup=folium.Popup(popup_html, max_width=320),
        color="#1a73e8",       # The blue border
        fill=True,
        fill_color="#1a73e8",  # The blue fill
        fill_opacity=0.7,
        weight=2
    ).add_to(cluster)


# In[ ]:


# ==========================================
# 4. DISPLAY THE LAYOUT (Replaces col1, col2)
# ==========================================

# 1. Let the map take over the entire screen width
st_folium(
    m, 
    use_container_width=True,  # Forces the map to stretch beautifully
    height=600, 
    returned_objects=[], 
    key="ngo_map"
)

st.markdown("<br>", unsafe_allow_html=True)

# 2. The Action Buttons (Keep these centered and wide)
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    st.link_button("⚠️ Report an Error", "https://forms.gle/K222YdwPCSsskNgw6", use_container_width=True, key="error_btn")
with btn_col2:
    st.link_button("➕ Add an NGO", "https://forms.gle/JSKwt8qH7Bw2ojBS9", use_container_width=True, key="add_btn")

st.markdown("<br>", unsafe_allow_html=True)

# 3. The Data Table (Tucked away neatly but still accessible)
with st.expander("📄 View Matching NGOs as a List"):

    # 1. Clean up the column names for the UI
    display_cols = ['NGO_name', 'Address', 'Contact_no'] 
    clean_df = df[display_cols].copy()
    clean_df.columns = ["NGO Name", "Location / Address", "Phone Number"]

    # 2. Inject modern web table CSS
    st.markdown("""
    <style>
    .modern-table {
        width: 100%;
        border-collapse: collapse;
        font-family: sans-serif;
        margin: 10px 0;
        font-size: 14px;
        border-radius: 8px 8px 0 0;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.05);
    }
    .modern-table thead tr {
        background-color: #1a73e8; /* Google Blue */
        color: #ffffff;
        text-align: left;
    }
    .modern-table th, .modern-table td {
        padding: 12px 15px;
    }
    .modern-table tbody tr {
        border-bottom: 1px solid #dddddd;
    }
    .modern-table tbody tr:nth-of-type(even) {
        background-color: #f8f9fa; /* Subtle alternating row color */
    }
    .modern-table tbody tr:last-of-type {
        border-bottom: 2px solid #1a73e8;
    }
    .modern-table tbody tr:hover {
        background-color: #e8f0fe; /* Light blue highlight on hover */
        transition: 0.2s;
    }
    </style>
    """, unsafe_allow_html=True)

    # 3. Convert the dataframe to HTML and render it with the custom CSS class
    html_table = clean_df.to_html(index=False, classes="modern-table", escape=False)
    st.markdown(html_table, unsafe_allow_html=True)


# In[ ]:





# In[ ]:





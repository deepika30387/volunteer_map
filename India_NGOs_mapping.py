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


# 1. UI Setup
st.set_page_config(layout="wide", page_title="India NGOs")
st.title("Find NGOs Near You")

# Location & Radius Inputs
st.sidebar.subheader("Your Location")
user_location = st.sidebar.text_input("Enter city or neighborhood (e.g., Bandra, Mumbai)")
search_radius_km = st.sidebar.slider("Search Radius (km)", min_value=1, max_value=50, value=10)

@st.cache_data
def load_data():
    df = pd.read_csv("guidestar_ngos_database_clean.csv").dropna(subset=['latitude', 'longitude'])   
    return df

df = load_data()


# 4. Map Setup
m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
cluster = MarkerCluster().add_to(m)

# 5. Geocode Volunteer & Apply Distance Filter
if user_location:

    geolocator = ArcGIS(user_agent="ngo_map_prototype")
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

        st.sidebar.success(f"Showing {len(df)} matching NGOs within {search_radius_km} km")
    else:
        st.sidebar.error("Location not found. Try adding a city name.")

# 6. Populate Pins on the Map
# for idx, row in df.iterrows():

#     # Build the HTML popup, now including the date_display variable
#     popup_html = f"""
#     <div style="font-family: sans-serif; font-size: 13px; min-width: 200px;">
#         <h4 style="margin: 0 0 5px 0; color: #1a73e8;">{row['NGO_name']}</h4>
#         <p style="margin: 2px 0;"><b>Contact:</b> {row.get('Contact')}</p>
#         <p style="margin: 2px 0;"><b>Phone:</b> {row.get('Contact_no')}</p>
#         <p style="margin: 2px 0 10px 0;"><b>Address:</b> {row['Address']}</p>        
#     </div>
#     """

#     folium.Marker(
#         location=[row['latitude'], row['longitude']],
#         popup=folium.Popup(popup_html, max_width=320),
#         icon=folium.Icon(color='red', icon='heart')
#     ).add_to(cluster)        

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

    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=folium.Popup(popup_html, max_width=320),
        icon=folium.Icon(color='red', icon='heart')
    ).add_to(cluster)


# In[ ]:


# 7. Layout Display
col1, col2 = st.columns([2, 1])

with col1:
    st_folium(
        m, 
        width=1000, 
        height=600, 
        returned_objects=[], 
        key="ngo_map"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Create two equal-width buttons directly below the map
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        st.link_button("⚠️ Report an Error",
                       "https://forms.gle/K222YdwPCSsskNgw6",
                       use_container_width=True,type="primary")

    with btn_col2:
        st.link_button("➕ Add an NGO",
                       "https://forms.gle/JSKwt8qH7Bw2ojBS9",                       
                       use_container_width=True,type="primary")

with col2:
    st.markdown("### Matching NGOs")
    display_cols = ['NGO_name', 'Address', 'Contact_no']

    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)


# In[ ]:





# In[ ]:





# In[ ]:





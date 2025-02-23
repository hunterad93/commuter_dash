import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import numpy as np
import os

def load_and_prepare_data():
    """Load and prepare data for visualization"""
    # Update the file path to be relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, '..', 'data', 'cleaned_surveys_facts.csv')
    df = pd.read_csv(data_path)
    
    # Filter to only rows with valid coordinates
    df = df.dropna(subset=['latitude', 'longitude'])
    
    # Calculate primary mode based on highest number of days
    mode_columns = ['days_walk', 'days_bike', 'days_drive_alone', 
                   'days_carpool', 'days_bus', 'days_other']
    
    # Convert non-numeric values to 0
    for col in mode_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Get the mode with maximum days for each row
    df['primary_mode'] = df[mode_columns].idxmax(axis=1)
    # Clean up the mode names by removing 'days_' prefix
    df['primary_mode'] = df['primary_mode'].str.replace('days_', '')
    
    return df

def add_jitter(coord, amount=0.0001):
    """Add random jitter to a coordinate"""
    return coord + np.random.uniform(-amount, amount)

def create_map(data):
    """Create a simple folium map with filtered data"""
    # Initialize the map centered on UM campus
    m = folium.Map(
        location=[46.860121625346494, -113.98524070374006],
        zoom_start=13
    )
    
    # Add dots for each person with jitter
    for _, row in data.iterrows():
        folium.CircleMarker(
            location=[
                add_jitter(row['latitude']),
                add_jitter(row['longitude'])
            ],
            radius=3,
            color='blue',
            fill=True,
            opacity=0.6,
            fill_opacity=0.6
        ).add_to(m)
    
    return m

def main():
    st.set_page_config(layout="wide")

    st.title('UM Commuter Map')
    
    # Load data
    df = load_and_prepare_data()
    
    # Sidebar filters
    st.sidebar.header('Filters')
    
    # Survey year filter
    years = sorted(df['survey_year'].unique())
    selected_year = st.sidebar.selectbox(
        'Survey Year',
        years,
        index=len(years)-1  # Default to most recent year
    )
    
    # Affiliation filter
    affiliations = sorted(df['primary_affiliation'].unique())
    selected_affiliations = st.sidebar.multiselect(
        'Affiliation',
        affiliations,
        default=affiliations
    )
    
    # Mode filter
    modes = sorted(df['primary_mode'].unique())
    selected_modes = st.sidebar.multiselect(
        'Primary Mode',
        modes,
        default=modes
    )
    
    # Student classification filter (only show if Students are selected)
    if 'Student' in selected_affiliations:
        student_classes = sorted(df[df['primary_affiliation'] == 'Student']['student_classification'].unique())
        selected_classes = st.sidebar.multiselect(
            'Student Classification',
            student_classes,
            default=student_classes
        )
    else:
        selected_classes = df['student_classification'].unique()
    
    # Apply filters
    filtered_df = df[
        (df['survey_year'] == selected_year) &
        (df['primary_affiliation'].isin(selected_affiliations)) &
        (df['primary_mode'].isin(selected_modes)) &
        (df['student_classification'].isin(selected_classes) | (df['student_classification'].isna()))
    ]
    
    # Display stats
    st.sidebar.header('Statistics')
    st.sidebar.write(f'Total commuters located: {len(filtered_df)}')
    
    # Create and display map
    m = create_map(filtered_df)
    folium_static(m)

if __name__ == "__main__":
    main()
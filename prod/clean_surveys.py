import pandas as pd
import numpy as np
import os
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

# Campus coordinates
CAMPUS_LAT = 46.860121625346494
CAMPUS_LON = -113.98524070374006

# Factor to convert straight-line to realistic travel distance
CIRCUITY_FACTOR = 1.35

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in miles using the haversine formula"""
    R = 3959  # Earth's radius in miles
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Apply circuity factor to convert straight-line to travel distance
    return R * c * CIRCUITY_FACTOR

def ensure_output_dir():
    """Create cleaning_output directory if it doesn't exist"""
    output_dir = Path('cleaning_output')
    output_dir.mkdir(exist_ok=True)
    return output_dir

def load_survey_data(filepath, year):
    """Load survey data with appropriate row handling and add year"""
    df = pd.read_csv(filepath, 
                     header=1,
                     skiprows=[2])
    df['survey_year'] = year
    # Ensure Response ID is present and handled correctly
    if 'Response ID' not in df.columns:
        raise ValueError(f"Response ID column not found in {year} dataset")
    
    # Standardize to ResponseId for consistency
    df = df.rename(columns={'Response ID': 'ResponseId'})
    return df

def consolidate_mode(mode):
    """Consolidate travel modes into main categories"""
    if not isinstance(mode, str) or pd.isna(mode):
        return None
        
    mode = mode.lower()
    
    if mode == 'did not travel':
        return None
    # Check for bus first, since some bus responses include "walk" in them
    elif any(x in mode for x in ['udash', 'mountain line', 'bus']):
        return 'Bus'
    elif 'walk' in mode:
        return 'Walk'
    elif 'bike' in mode:
        return 'Bike'
    elif 'drive alone' in mode:
        return 'Drive Alone'
    elif any(x in mode for x in ['carpool', 'vanpool']):
        return 'Carpool'
    else:
        return 'Other'

def consolidate_affiliation(affiliation):
    """Consolidate affiliations into main categories"""
    if not isinstance(affiliation, str) or pd.isna(affiliation):
        return None
        
    if 'Student' in affiliation:
        return 'Student'
    elif 'Faculty' in affiliation:
        return 'Faculty'
    elif 'Staff' in affiliation:
        return 'Staff'
    return affiliation

def get_common_columns(df_2024, df_2021, start_col):
    """Get columns that exist in both datasets, starting from specified column"""
    # Find the exact column name that matches (case-insensitive)
    matching_cols_2024 = [col for col in df_2024.columns 
                         if col.lower() == start_col.lower()]
    
    if not matching_cols_2024:
        raise ValueError(f"Could not find column matching '{start_col}' in 2024 dataset")
    
    actual_col = matching_cols_2024[0]
    start_idx = df_2024.columns.get_loc(actual_col)
    
    # Get columns from starting point, but always include ResponseId
    cols_2024 = list(df_2024.columns[start_idx:])
    if 'ResponseId' not in cols_2024:
        cols_2024 = ['ResponseId'] + cols_2024
    
    cols_2021 = df_2021.columns
    
    # Find common columns
    common_cols = list(set(cols_2024).intersection(set(cols_2021)))
    # Ensure ResponseId and survey_year are included
    for required_col in ['ResponseId', 'survey_year']:
        if required_col not in common_cols:
            common_cols.append(required_col)
    
    return common_cols

def process_student_modes(row, day_cols):
    """Process travel modes for a single student"""
    modes = []
    for col in day_cols:
        mode = consolidate_mode(row[col])
        if mode is not None:
            modes.append(mode)
    return modes

def process_travel_modes(df):
    """Process daily travel mode columns into mode frequency columns"""
    df = df.copy()
    
    # Find travel mode columns
    travel_patterns = [
        "For each day last week, what was your primary mode of travel between your residence and campus?",
        "For each day last week, what was your primary mode of travel between your residence and other parts of campus?"
    ]
    
    # Find day columns
    day_cols = []
    for col in df.columns:
        for pattern in travel_patterns:
            if pattern in col:
                if any(day in col for day in [' Sun', ' Mon', ' Tues', ' Wed', ' Thurs', ' Fri', ' Sat']):
                    day_cols.append(col)
    
    if not day_cols:
        return df
    
    # Process mode frequencies
    modes = ['Walk', 'Bike', 'Drive Alone', 'Carpool', 'Bus', 'Other']
    for mode in modes:
        df[f'Days {mode}'] = 0
    
    # Process each student
    for idx in df.index:
        student_modes = process_student_modes(df.iloc[idx], day_cols)
        
        # Count frequencies for this student
        for mode in modes:
            mode_count = student_modes.count(mode)
            df.at[idx, f'Days {mode}'] = mode_count
    
    # Drop original day columns
    df = df.drop(columns=day_cols)
    
    return df

def get_column_mappings():
    """Define column mappings for standardization"""
    # Keep existing 2021 column mapping as is
    column_mapping_2021 = {
        'Approximately how many miles do you commute to campus every day (one way)?': 
            'Approximately how many miles do you commute to campus every day (one way)? Feel free to use the image below to quickly get a sense of your distance from UM.',
        
        'How satisfying was your experience using the UDASH or Mountain Line bus system?':
            'How satisfying was your experience using the UDASH bus system?',
        
        'Have you ever used the Mountain Line or UDASH tracking apps?':
            'Have you ever used the Transit app to track UDASH or Mountain Line buses?',
        
        'Do you support or oppose the use of electric scooters (so-called e-scooters) in the Missoula area and on campus? (choose one)':
            'Do you support or oppose the use of electric scooters (e-scooters) in the Missoula area and on campus? (choose one)',
        
        'If a company establishes an e-scooter share system in Missoula that allows riders to rent e-scooters, how likely are you to use an e-scooter share system?':
            'If a company establishes an e-scooter and e-bike share system in Missoula (Lime, Spin, etc.) that allows riders to rent bikes and scooters, do you anticipate using this service?'
    }
    
    # Complete mapping for standardized column names
    standardized_names = {
        'What is your primary affiliation with the University of Montana?': 'primary_affiliation',
        'Approximately how many miles do you commute to campus every day (one way)? Feel free to use the image below to quickly get a sense of your distance from UM.': 'commute_miles',
        'How satisfying was your experience using the UDASH bus system?': 'udash_satisfaction',
        'Have you ever used the Transit app to track UDASH or Mountain Line buses?': 'transit_app_usage',
        'Do you support or oppose the use of electric scooters (e-scooters) in the Missoula area and on campus? (choose one)': 'escooter_support',
        'If a company establishes an e-scooter and e-bike share system in Missoula (Lime, Spin, etc.) that allows riders to rent bikes and scooters, do you anticipate using this service?': 'escooter_usage_intent',
        
        # Travel mode counts
        'Days Walk': 'days_walk',
        'Days Bike': 'days_bike',
        'Days Drive Alone': 'days_drive_alone',
        'Days Carpool': 'days_carpool',
        'Days Bus': 'days_bus',
        'Days Other': 'days_other',
        
        # New standardized names
        'On average, how many round trips to campus do you make per week?': 'weekly_trips',
        'What keeps you, if anything, from riding a bicycle more often? (select all that apply) - Selected Choice': 'bike_barriers',
        'What keeps you, if anything, from riding a bicycle more often? (select all that apply) - Other, please specify - Text': 'bike_barriers_other',
        'You indicated that you sometimes carpool to campus. How many people, besides yourself, are usually in the vehicle when you carpool?': 'carpool_occupants',
        'When you drive to campus, where do you most frequently park your vehicle? - Selected Choice': 'parking_location',
        'When you drive to campus, where do you most frequently park your vehicle? - Other - Text': 'parking_location_other',
        'What are the two intersecting streets ("cross streets") nearest to where you live?(e.g. 5th & Gerald)': 'cross_streets',
        'How important are each of the following to making biking to campus more appealing to you? - Plowed routes during the winter months': 'bike_importance_plowed_routes',
        'How important are each of the following to making biking to campus more appealing to you? - Protected bike lanes to/from campus': 'bike_importance_protected_lanes',
        'How important are each of the following to making biking to campus more appealing to you? - Availability and location of bike parking on campus': 'bike_importance_parking',
        'How important are each of the following to making biking to campus more appealing to you? - Access to a free or low cost bike mechanic': 'bike_importance_mechanic',
        'How important are each of the following to making biking to campus more appealing to you? - Access to a bike (rental or low cost purchase)': 'bike_importance_access',
        'Where is your University-owned residence? - Selected Choice': 'university_residence',
        'Where is your University-owned residence? - Other (please specify) - Text': 'university_residence_other',
        'With which gender do you identify? - Selected Choice': 'gender',
        'With which gender do you identify? - Not listed - Text': 'gender_other',
        'Which of the following best describes you? Please select one.': 'ethnicity',
        'Describe your commute to UM in five words or less.': 'commute_description',
        'Do you currently live in University-owned housing?': 'lives_in_university_housing',
        'Are you a full-time or part-time affiliate?': 'enrollment_status',
        'If your experience riding the bus was unsatisfying, please tell us why in the space below.': 'bus_dissatisfaction_reason',
        'How would you describe your experience using the app?': 'transit_app_experience',
        'Please indicate how you perceive of the following types of commuters. - Public transit riders': 'perception_transit_riders',
        'Please indicate how you perceive of the following types of commuters. - Motorists': 'perception_motorists',
        'Please indicate how you perceive of the following types of commuters. - Bicyclists': 'perception_bicyclists',
        'What is your age?': 'age',
        'If your permanent address is not in Missoula, how many times per year do you travel home (your permanent address) for holidays, weekends, breaks, etc.?': 'yearly_home_trips',
        'If you commute via personal vehicle to campus, please indicate the type of vehicle.': 'vehicle_type',
        "If you're a student, what is your primary classification? - Selected Choice": 'student_classification',
        "If you're a student, what is your primary classification? - Other - Text": 'student_classification_other',
        'Would any of the incentives below encourage you to carpool with fellow UM commuters on an occasional basis? (select all incentives that are appealing)': 'carpool_incentives',
        'On which campuses do you work or attend classes?': 'campus_location',
        'What is the zip code of your permanent address?': 'permanent_zipcode',
        'What keeps you, if anything, from using public transit more often? (select all that apply) - Selected Choice': 'transit_barriers',
        'What keeps you, if anything, from using public transit more often? (select all that apply) - Other - please specify: - Text': 'transit_barriers_other',
        'What type of parking permit do you have, if any?(Check all that apply.)': 'parking_permit',
        'What is your typical mode of transport when traveling to your permanent address for holidays, breaks, etc.? - Selected Choice': 'home_travel_mode',
        'What is your typical mode of transport when traveling to your permanent address for holidays, breaks, etc.? - Other - Text': 'home_travel_mode_other',
        'survey_year': 'survey_year'
    }
    
    return column_mapping_2021, standardized_names

def load_intersection_data(year):
    """Load intersection lookup data for a specific year"""
    filepath = Path(f'mapping_data/intersection_lookup_{year}.csv')
    if not filepath.exists():
        return None
    
    df = pd.read_csv(filepath)
    # Create lookup dictionary with ResponseId as key and (lat, lon) as value
    lookup = {
        row['ResponseId']: (row['matched_lat'], row['matched_lon'])
        for _, row in df.iterrows()
        if pd.notna(row['matched_lat']) and pd.notna(row['matched_lon'])
    }
    return lookup

def add_location_data(df, year):
    """Add latitude, longitude, and calculated distance columns from intersection lookup data"""
    df = df.copy()
    
    # Initialize location columns
    df['latitude'] = None
    df['longitude'] = None
    df['calculated_distance_mi'] = None
    
    # Load intersection lookup data
    lookup = load_intersection_data(year)
    if lookup is None:
        return df
    
    # Update location data for matching ResponseIds
    for response_id, (lat, lon) in lookup.items():
        mask = df['ResponseId'] == response_id
        df.loc[mask, 'latitude'] = lat
        df.loc[mask, 'longitude'] = lon
        
        # Calculate distance if coordinates are valid
        if pd.notna(lat) and pd.notna(lon):
            distance = calculate_haversine_distance(
                CAMPUS_LAT, CAMPUS_LON,
                lat, lon
            )
            df.loc[mask, 'calculated_distance_mi'] = distance
    
    return df

def clean_survey_data(input_filepath, year, start_col, output_dir):
    """Main function to clean survey data"""
    # Get column mappings
    column_mapping_2021, standardized_names = get_column_mappings()
    
    # Load data
    df = load_survey_data(input_filepath, year)
    
    # Apply 2021 column mapping if it's the 2021 dataset
    if year == 2021:
        df = df.rename(columns=column_mapping_2021)
    
    # Filter columns but always keep ResponseId
    start_idx = df.columns.get_loc(start_col)
    cols = list(df.columns[start_idx:])
    cols = ['ResponseId'] + cols + ['survey_year']
    cols = list(dict.fromkeys(cols))  # Remove any duplicates while preserving order
    df = df[cols]
    
    # Process travel modes
    df = process_travel_modes(df)
    
    # Add location data
    df = add_location_data(df, year)
    
    # Consolidate affiliations
    affiliation_col = 'What is your primary affiliation with the University of Montana?'
    if affiliation_col in df.columns:
        df[affiliation_col] = df[affiliation_col].apply(consolidate_affiliation)
    
    return df

def get_column_categories():
    """Define which columns belong in facts vs opinions datasets"""
    fact_columns = [
        'ResponseId',
        'survey_year',
        'primary_affiliation',
        'commute_miles',
        'calculated_distance_mi',
        'days_walk',
        'days_bike',
        'days_drive_alone',
        'days_carpool',
        'days_bus',
        'days_other',
        'weekly_trips',
        'carpool_occupants',
        'parking_location',
        'cross_streets',
        'university_residence',
        'gender',
        'ethnicity',
        'lives_in_university_housing',
        'enrollment_status',
        'age',
        'yearly_home_trips',
        'vehicle_type',
        'student_classification',
        'campus_location',
        'permanent_zipcode',
        'parking_permit',
        'home_travel_mode',
        'latitude',
        'longitude'
    ]

    opinion_columns = [
        'ResponseId',
        'survey_year',
        'udash_satisfaction',
        'transit_app_usage',
        'escooter_support',
        'escooter_usage_intent',
        'bike_barriers',
        'bike_barriers_other',
        'bike_importance_plowed_routes',
        'bike_importance_protected_lanes',
        'bike_importance_parking',
        'bike_importance_mechanic',
        'bike_importance_access',
        'commute_description',
        'bus_dissatisfaction_reason',
        'transit_app_experience',
        'perception_transit_riders',
        'perception_motorists',
        'perception_bicyclists',
        'carpool_incentives',
        'transit_barriers',
        'transit_barriers_other'
    ]
    
    return fact_columns, opinion_columns

def main():
    # Create or ensure output directory exists
    output_dir = ensure_output_dir()
    
    # Process both years
    df_2024 = clean_survey_data(
        '/Users/adamhunter/Documents/eva_freelance/dev/UM Commuter Survey fall 2024_January 9, 2025_12.15.csv',
        2024,
        'What is your primary affiliation with the University of Montana?',
        output_dir
    )

    df_2021 = clean_survey_data(
        '/Users/adamhunter/Documents/eva_freelance/dev/UM Commuter Survey fall 2021_August 22, 2023_12.45.csv',
        2021,
        'What is your primary affiliation with the University of Montana?',
        output_dir
    )

    # Get common columns between both years
    common_cols = get_common_columns(df_2024, df_2021,
        'What is your primary affiliation with the University of Montana?')

    # Combine datasets with only common columns
    df_combined = pd.concat([
        df_2024[common_cols],
        df_2021[common_cols]
    ], ignore_index=True)

    # Apply standardized column names
    _, standardized_names = get_column_mappings()
    df_combined = df_combined.rename(columns=standardized_names)

    # Save final combined dataset
    df_combined.to_csv(output_dir / 'cleaned_surveys.csv', index=False)

    # Split into fact and opinion datasets
    fact_columns, opinion_columns = get_column_categories()
    
    # Create fact and opinion dataframes, keeping only columns that exist in df_combined
    fact_columns = [col for col in fact_columns if col in df_combined.columns]
    opinion_columns = [col for col in opinion_columns if col in df_combined.columns]
    
    df_facts = df_combined[fact_columns]
    df_opinions = df_combined[opinion_columns]
    
    # Save split datasets
    df_facts.to_csv(output_dir / 'cleaned_surveys_facts.csv', index=False)
    df_opinions.to_csv(output_dir / 'cleaned_surveys_opinions.csv', index=False)

if __name__ == "__main__":
    main()
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Emissions factors in kg CO2e per mile
EMISSIONS_FACTORS = {
    'drive_alone': 0.32590725,    # Automobile
    'carpool': 0.16295363,        # Carpool (half of automobile)
    'bus': 0.06524557,            # Public Bus
    'bike': 0,                    # Non-motorized
    'walk': 0,                    # Non-motorized
    'other': 0                    # Assume zero for unknown modes
}

ACADEMIC_WEEKS = 28  # Number of weeks in academic year

def load_and_calculate_data():
    """Load data and calculate miles and emissions by mode"""
    df = pd.read_csv('cleaned_surveys_facts.csv')
    
    # Convert days columns to numeric, replacing NaN with 0
    mode_columns = ['days_walk', 'days_bike', 'days_drive_alone', 
                   'days_carpool', 'days_bus', 'days_other']
    
    for col in mode_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Calculate miles and emissions per mode
    for mode in mode_columns:
        mode_name = mode[5:]  # Remove 'days_' prefix
        
        # Calculate miles
        miles_col = f'miles_{mode_name}'
        df[miles_col] = df[mode] * df['commute_miles'] * 2
        
        # Calculate emissions
        emissions_col = f'emissions_{mode_name}'
        df[emissions_col] = df[miles_col] * EMISSIONS_FACTORS.get(mode_name, 0)
    
    return df

def format_number(num):
    """Format large numbers to abbreviated form (e.g., 53k, 1.2M)"""
    if abs(num) >= 1_000_000:
        return f'{num/1_000_000:.1f}M'
    elif abs(num) >= 1_000:
        return f'{num/1_000:.1f}k'
    return f'{num:.1f}'

def create_mode_chart(data, years, metric='miles', per_capita=False, time_period='week'):
    """Create horizontal bar chart of selected metric by mode with year comparison"""
    # Get relevant columns based on metric
    if metric == 'miles':
        columns = ['miles_walk', 'miles_bike', 'miles_drive_alone', 
                  'miles_carpool', 'miles_bus', 'miles_other']
        title_metric = 'Miles'
    else:  # emissions
        columns = ['emissions_walk', 'emissions_bike', 'emissions_drive_alone', 
                  'emissions_carpool', 'emissions_bus', 'emissions_other']
        title_metric = 'kg CO2e'
    
    # Create data for each year
    year_data = {}
    for year in years:
        year_df = data[data['survey_year'] == year]
        
        if per_capita:
            mode_totals = {
                col.split('_', 1)[1].replace('_', ' ').title(): year_df[col].mean()
                for col in columns
            }
            title_prefix = 'Average'
        else:
            mode_totals = {
                col.split('_', 1)[1].replace('_', ' ').title(): year_df[col].sum()
                for col in columns
            }
            title_prefix = 'Total'
            
        # Apply academic year multiplier if needed
        if time_period == 'academic_year':
            mode_totals = {k: v * ACADEMIC_WEEKS for k, v in mode_totals.items()}
            time_period_text = 'Academic Year'
        else:
            time_period_text = 'Weekly'
            
        year_data[year] = mode_totals
    
    # Get all modes and sort by maximum value across years
    all_modes = list(year_data[years[0]].keys())
    max_values = {mode: max(year_data[year][mode] for year in years) 
                 for mode in all_modes}
    sorted_modes = sorted(all_modes, key=lambda x: max_values[x], reverse=False)  # Changed to ascending
    
    # Create traces for each year
    fig = go.Figure()
    
    for year in years:
        fig.add_trace(go.Bar(
            name=str(year),
            y=sorted_modes,
            x=[year_data[year][mode] for mode in sorted_modes],
            orientation='h',
            text=[format_number(year_data[year][mode]) for mode in sorted_modes],
            textposition='outside',
            textfont=dict(size=14),
        ))
    
    fig.update_layout(
        title=f'{title_prefix} {time_period_text} {title_metric} by Mode',
        xaxis_title=f'{time_period_text} {title_metric}',
        yaxis_title='Mode',
        barmode='group',
        height=600,  # Increased height
        yaxis=dict(
            tickfont=dict(size=14),  # Increase y-axis label size
            autorange=True  # Changed from "reversed" to show highest values at top
        ),
        xaxis=dict(
            tickfont=dict(size=12)  # Increase x-axis label size
        ),
        showlegend=True,
        legend=dict(
            font=dict(size=14),  # Increase legend text size
            yanchor="bottom",  # Changed from "top"
            y=0.01,           # Changed from 0.99
            xanchor="right",
            x=0.99
        ),
        margin=dict(l=20, r=20, t=40, b=20),  # Adjust margins
        bargap=0.2,  # Adjust gap between bars
        bargroupgap=0.1  # Adjust gap between bar groups
    )
    return fig

def main():
    st.set_page_config(layout="wide")

    st.title('UM Commuter Analysis')
    
    # Load data
    df = load_and_calculate_data()
    
    # Sidebar filters
    st.sidebar.header('Filters')
    
    # Survey year filter with default values [2024, 2021]
    years = sorted(df['survey_year'].unique())
    selected_years = st.sidebar.multiselect(
        'Survey Year',
        years,
        default=[2024, 2021]
    )
    
    if not selected_years:
        st.error("Please select at least one survey year.")
        return
    
    # Rest of the filters remain the same
    metric = st.sidebar.selectbox(
        'Metric',
        ['Miles', 'Emissions'],
        index=0,  # Select first option (Miles)
        format_func=lambda x: 'Miles' if x == 'Miles' else 'kg CO2e'
    )
    
    per_capita = st.sidebar.selectbox(
        'View',
        ['Total', 'Per Capita'],
        index=1  # Select second option (Per Capita)
    ) == 'Per Capita'
    
    time_period = st.sidebar.selectbox(
        'Time Period',
        ['Week', 'Academic Year'],
        index=1,  # Select second option (Academic Year)
        format_func=lambda x: 'Weekly' if x == 'Week' else 'Academic Year'
    ).lower().replace(' ', '_')
    
    affiliations = sorted([x for x in df['primary_affiliation'].unique() if pd.notna(x)])
    selected_affiliations = st.sidebar.multiselect(
        'Affiliation',
        affiliations,
        default=['Faculty', 'Staff', 'Student']
    )
    
    # Apply filters
    filtered_df = df[
        (df['survey_year'].isin(selected_years)) &
        (df['primary_affiliation'].isin(selected_affiliations))
    ]
    
    # Display summary statistics for each selected year
    st.sidebar.header('Summary Statistics')
    
    for year in selected_years:
        year_df = filtered_df[filtered_df['survey_year'] == year]
        
        if metric == 'Miles':
            total_weekly = year_df[[
                'miles_walk', 'miles_bike', 'miles_drive_alone',
                'miles_carpool', 'miles_bus', 'miles_other'
            ]].sum().sum()
            metric_unit = 'miles'
        else:
            total_weekly = year_df[[
                'emissions_walk', 'emissions_bike', 'emissions_drive_alone',
                'emissions_carpool', 'emissions_bus', 'emissions_other'
            ]].sum().sum()
            metric_unit = 'kg CO2e'
        
        multiplier = ACADEMIC_WEEKS if time_period == 'academic_year' else 1
        total = total_weekly * multiplier
        
        st.sidebar.write(f'### {year}')
        st.sidebar.write(f'Total commuters: {format_number(len(year_df))}')
        st.sidebar.write(f'Total {metric_unit}: {format_number(total)}')
        st.sidebar.write(f'Average {metric_unit} per person: {format_number(total/len(year_df))}')
    
    # Display horizontal bar chart
    st.plotly_chart(create_mode_chart(filtered_df,
                                     selected_years,
                                     metric.lower(), 
                                     per_capita,
                                     time_period), 
                    use_container_width=True)

if __name__ == "__main__":
    main()
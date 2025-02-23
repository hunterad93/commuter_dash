import pandas as pd
import plotly.graph_objects as go

def analyze_long_distance_trends():
    """Analyze trends in long-distance drivers (>15 miles)"""
    # Load data
    df = pd.read_csv('cleaning_output/cleaned_surveys_facts.csv')
    
    # Calculate total drive days
    df['total_drive_days'] = df['days_drive_alone'] + df['days_carpool']
    
    # Filter for drivers only (at least 1 day of driving)
    df_drivers = df[df['total_drive_days'] > 0]
    
    # Calculate percentages for each year
    results = []
    for year in sorted(df['survey_year'].unique()):
        year_data = df_drivers[df_drivers['survey_year'] == year]
        total_drivers = len(year_data)
        long_distance = len(year_data[year_data['commute_miles'] > 15])
        
        percentage = (long_distance / total_drivers) * 100
        results.append({
            'year': year,
            'total_drivers': total_drivers,
            'long_distance': long_distance,
            'percentage': percentage
        })
        
        print(f"\nYear: {year}")
        print(f"Total drivers: {total_drivers}")
        print(f"Long distance drivers: {long_distance}")
        print(f"Percentage: {percentage:.1f}%")
    
    # Create bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=[str(r['year']) for r in results],
        y=[r['percentage'] for r in results],
        text=[f"{r['percentage']:.1f}%" for r in results],
        textposition='auto',
    ))
    
    fig.update_layout(
        title_text='Percentage of Drivers >15 Miles from Campus',
        height=500,
        width=600,
        yaxis_title='Percent of Drivers',
        showlegend=False,
        yaxis_range=[0, max([r['percentage'] for r in results]) * 1.1]  # Add 10% padding
    )
    
    # Save as high-resolution PNG
    fig.write_image("long_distance_drivers_trends.png", scale=3)

if __name__ == "__main__":
    analyze_long_distance_trends()
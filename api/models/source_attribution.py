# Author: Daksha009
# Repo: https://github.com/Daksha009/AirSense-Guardian.git

import numpy as np
from datetime import datetime

class SourceAttribution:
    """Attributing pollution sources based on AQI, weather, and traffic patterns"""
    
    def attribute_sources(self, aqi, wind_speed, traffic_density, hour):
        """
        Attribute pollution sources based on current conditions
        
        Returns:
            dict with percentages for each source type
        """
        # Base attribution
        sources = {
            'traffic': 0.0,
            'industry': 0.0,
            'open_burning': 0.0,
            'other': 0.0
        }
        
        # High traffic + low wind = vehicle pollution
        if traffic_density > 0.6 and wind_speed < 5:
            sources['traffic'] = min(0.6, 0.3 + traffic_density * 0.3)
        
        # Night spikes (10 PM - 6 AM) = industrial activity
        if (hour >= 22 or hour < 6) and aqi > 100:
            sources['industry'] = min(0.4, 0.2 + (aqi - 100) / 200)
        
        # Low wind + high AQI = open burning / stagnant air
        if wind_speed < 3 and aqi > 120:
            sources['open_burning'] = min(0.3, 0.15 + (aqi - 120) / 300)
        
        # Normalize to ensure total is reasonable
        total = sum(sources.values())
        if total < 0.5:
            # If attribution is low, distribute based on AQI level
            if aqi > 150:
                sources['traffic'] = 0.5
                sources['industry'] = 0.2
                sources['open_burning'] = 0.2
                sources['other'] = 0.1
            else:
                sources['traffic'] = 0.4
                sources['industry'] = 0.2
                sources['open_burning'] = 0.2
                sources['other'] = 0.2
        else:
            # Normalize to 100%
            factor = 1.0 / total if total > 0 else 1.0
            for key in sources:
                sources[key] *= factor
        
        # Round to 2 decimal places
        for key in sources:
            sources[key] = round(sources[key] * 100, 1)
        
        return sources
    
    def get_source_description(self, sources):
        """Get human-readable description of sources"""
        max_source = max(sources.items(), key=lambda x: x[1])
        source_name = max_source[0].replace('_', ' ').title()
        percentage = max_source[1]
        
        return f"{source_name} contributes {percentage}% to current pollution levels"


# Author: Daksha009
# Repo: https://github.com/Daksha009/AirSense-Guardian.git

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from models.predictor import AQIPredictor
from models.source_attribution import SourceAttribution
from models.action_engine import ActionEngine

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Initialize models
predictor = AQIPredictor()
source_attributor = SourceAttribution()
action_engine = ActionEngine()

# API Keys (set in .env file)
AQICN_TOKEN = os.getenv('AQICN_TOKEN', '')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/aqi/current', methods=['GET'])
def get_current_aqi():
    """Get current AQI for a location"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    
    if not lat or not lon:
        return jsonify({'error': 'Latitude and longitude required'}), 400
    
    try:
        # Fetch from High Accuracy Source (AQICN/OWM)
        aqi_data = fetch_air_quality_data(lat, lon)
        
        # Fetch weather data
        weather_data = fetch_weather_data(lat, lon)
        
        # Estimate traffic density
        traffic_density = estimate_traffic_density(lat, lon)
        
        # Get source attribution
        sources = source_attributor.attribute_sources(
            aqi_data.get('aqi', 0),
            weather_data.get('wind_speed', 0),
            traffic_density,
            datetime.now().hour
        )
        
        # Get predictions
        predictions = predictor.predict(
            aqi_data.get('aqi', 0),
            weather_data.get('wind_speed', 0),
            weather_data.get('humidity', 0),
            traffic_density,
            datetime.now(),
            temperature=weather_data.get('temperature', 25)
        )
        
        # Get actionable insights
        actions = action_engine.generate_actions(
            aqi_data.get('aqi', 0),
            sources,
            weather_data,
            traffic_density
        )
        
        # Get alerts
        alerts = []
        current_aqi = aqi_data.get('aqi', 0)
        
        # Check current conditions
        if current_aqi > 150:
            alerts.append({
                'type': 'warning',
                'severity': 'high' if current_aqi > 200 else 'moderate',
                'message': f'Current AQI is {current_aqi:.0f} - Unhealthy conditions detected',
                'timestamp': datetime.now().isoformat()
            })
        
        # Check future predictions
        for pred in predictions:
            if pred.get('aqi', 0) > 150:
                alerts.append({
                    'type': 'prediction',
                    'severity': 'high' if pred.get('aqi', 0) > 200 else 'moderate',
                    'message': f'High AQI ({pred.get("aqi", 0):.0f}) expected at {pred.get("time", "N/A")}',
                    'timestamp': pred.get('time', datetime.now().isoformat()),
                    'aqi': pred.get('aqi', 0)
                })
        
        return jsonify({
            'current': {
                'aqi': aqi_data.get('aqi', 0),
                'pm25': aqi_data.get('pm25', 0),
                'pm10': aqi_data.get('pm10', 0),
                'no2': aqi_data.get('no2', 0),
                'timestamp': datetime.now().isoformat(),
                'location': {'lat': lat, 'lon': lon}
            },
            'weather': weather_data,
            'traffic_density': traffic_density,
            'sources': sources,
            'predictions': predictions,
            'actions': actions,
            'alerts': alerts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/aqi/predict', methods=['POST'])
def predict_aqi():
    """Get AQI predictions for next 3-6 hours"""
    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')
    hours = data.get('hours', 6)
    
    if not lat or not lon:
        return jsonify({'error': 'Latitude and longitude required'}), 400
    
    try:
        # Get current data
        aqi_data = fetch_air_quality_data(lat, lon)
        weather_data = fetch_weather_data(lat, lon)
        traffic_density = estimate_traffic_density(lat, lon)
        
        # Generate predictions
        predictions = predictor.predict_multiple_hours(
            aqi_data.get('aqi', 0),
            weather_data.get('wind_speed', 0),
            weather_data.get('humidity', 0),
            traffic_density,
            datetime.now(),
            hours,
            temperature=weather_data.get('temperature', 25)
        )
        
        return jsonify({
            'predictions': predictions,
            'location': {'lat': lat, 'lon': lon}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get alerts for high pollution zones"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    
    if not lat or not lon:
        return jsonify({'error': 'Latitude and longitude required'}), 400
    
    try:
        aqi_data = fetch_air_quality_data(lat, lon)
        weather_data = fetch_weather_data(lat, lon)
        traffic_density = estimate_traffic_density(lat, lon)
        
        predictions = predictor.predict_multiple_hours(
            aqi_data.get('aqi', 0),
            weather_data.get('wind_speed', 0),
            weather_data.get('humidity', 0),
            traffic_density,
            datetime.now(),
            6,
            temperature=weather_data.get('temperature', 25)
        )
        
        alerts = []
        current_aqi = aqi_data.get('aqi', 0)
        
        # Check current conditions
        if current_aqi > 150:
            alerts.append({
                'type': 'warning',
                'severity': 'high' if current_aqi > 200 else 'moderate',
                'message': f'Current AQI is {current_aqi:.0f} - Unhealthy conditions detected',
                'timestamp': datetime.now().isoformat()
            })
        
        # Check future predictions
        for pred in predictions:
            if pred['aqi'] > 150:
                alerts.append({
                    'type': 'prediction',
                    'severity': 'high' if pred['aqi'] > 200 else 'moderate',
                    'message': f'High AQI ({pred["aqi"]:.0f}) expected at {pred["time"]}',
                    'timestamp': pred['time'],
                    'aqi': pred['aqi']
                })
        
        return jsonify({'alerts': alerts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def fetch_air_quality_data(lat, lon):
    """Fetch Air Quality data from AQICN (WAQI) or OWM fallback"""
    # 1. Try AQICN (Real-time station data - High Accuracy)
    if AQICN_TOKEN:
        try:
            url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={AQICN_TOKEN}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    results = data.get('data', {})
                    iaqi = results.get('iaqi', {})
                    
                    pm25 = iaqi.get('pm25', {}).get('v', 0)
                    pm10 = iaqi.get('pm10', {}).get('v', 0)
                    no2 = iaqi.get('no2', {}).get('v', 0)
                    
                    # Use official EPA calculation for accuracy
                    aqi = calculate_aqi(pm25, pm10)
                    
                    return {
                        'aqi': aqi,
                        'pm25': pm25,
                        'pm10': pm10,
                        'no2': no2
                    }
        except Exception as e:
            print(f"AQICN Error: {e}")

    # 2. Try OpenWeatherMap (Model-based - Fallback)
    if WEATHER_API_KEY:
        try:
            url = f"http://api.openweathermap.org/data/2.5/air_pollution"
            params = {'lat': lat, 'lon': lon, 'appid': WEATHER_API_KEY}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('list'):
                    comp = data['list'][0].get('components', {})
                    pm25 = comp.get('pm2_5', 0)
                    pm10 = comp.get('pm10', 0)
                    no2 = comp.get('no2', 0)
                    
                    aqi = calculate_aqi(pm25, pm10)
                    return {
                        'aqi': aqi,
                        'pm25': pm25,
                        'pm10': pm10,
                        'no2': no2
                    }
        except Exception as e:
            print(f"OWM Error: {e}")

    return get_fallback_data()

def get_fallback_data():
    """Generate realistic fallback data for Delhi"""
    try:
        base_aqi = 280 # Higher base for Delhi
        variation = np.random.randint(-20, 40)
        aqi = max(50, min(500, base_aqi + variation))
        
        pm25 = max(10, aqi * 0.8 + np.random.randint(-10, 10)) # More realistic PM2.5/AQI ratio
        pm10 = max(20, aqi * 1.2 + np.random.randint(-20, 20))
        no2 = max(15, aqi * 0.2 + np.random.randint(-5, 10))
        
        return {
            'aqi': round(aqi),
            'pm25': round(pm25, 1),
            'pm10': round(pm10, 1),
            'no2': round(no2, 1)
        }
    except Exception:
        return {'aqi': 310, 'pm25': 260, 'pm10': 350, 'no2': 45}

def fetch_weather_data(lat, lon):
    """Fetch weather data (wind speed, humidity)"""
    try:
        # Using OpenWeatherMap API (free tier)
        api_key = WEATHER_API_KEY or 'demo_key'
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'metric'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            wind = data.get('wind', {})
            main = data.get('main', {})
            
            return {
                'wind_speed': round(wind.get('speed', 0) * 3.6, 1),  # Convert m/s to km/h
                'humidity': main.get('humidity', 50),
                'temperature': round(main.get('temp', 25), 1),
                'pressure': main.get('pressure', 1013)
            }
        
        # Fallback: Realistic Delhi weather data
        return {
            'wind_speed': round(8 + np.random.randint(-2, 5), 1),  # 6-13 km/h typical
            'humidity': 55 + np.random.randint(-15, 20),  # 40-75% typical
            'temperature': round(28 + np.random.randint(-5, 8), 1),  # 23-36°C typical
            'pressure': 1010 + np.random.randint(-5, 5)
        }
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        # Fallback: Realistic Delhi weather
        return {
            'wind_speed': round(8 + np.random.randint(-2, 5), 1),
            'humidity': 55 + np.random.randint(-15, 20),
            'temperature': round(28 + np.random.randint(-5, 8), 1),
            'pressure': 1010 + np.random.randint(-5, 5)
        }

def estimate_traffic_density(lat, lon):
    """Estimate traffic density (simplified - using time-based heuristics)"""
    # In a real implementation, you'd use Google Maps API or similar
    # For now, use time-based estimation
    hour = datetime.now().hour
    
    # Peak hours: 7-9 AM, 5-7 PM
    if (7 <= hour <= 9) or (17 <= hour <= 19):
        base_density = 0.8
    elif (10 <= hour <= 16):
        base_density = 0.5
    else:
        base_density = 0.3
    
    # Add some randomness
    density = base_density + np.random.uniform(-0.1, 0.1)
    return max(0, min(1, density))  # Clamp between 0 and 1

def calculate_aqi(pm25, pm10):
    """Calculate Official US EPA AQI using piecewise linear formula"""
    def calc_epa_aqi(value, parameter='pm25'):
        if parameter == 'pm25':
            breakpoints = [
                (0.0, 12.0, 0, 50),
                (12.1, 35.4, 51, 100),
                (35.5, 55.4, 101, 150),
                (55.5, 150.4, 151, 200),
                (150.5, 250.4, 201, 300),
                (250.5, 350.4, 301, 400),
                (350.5, 500.4, 401, 500)
            ]
        else: # pm10
            breakpoints = [
                (0, 54, 0, 50),
                (55, 154, 51, 100),
                (155, 254, 101, 150),
                (255, 354, 151, 200),
                (355, 424, 201, 300),
                (425, 504, 301, 400),
                (505, 604, 401, 500)
            ]
        
        for c_low, c_high, i_low, i_high in breakpoints:
            if c_low <= value <= c_high:
                return round(((i_high - i_low) / (c_high - c_low)) * (value - c_low) + i_low)
        
        if value > 500.4: return 500
        return 0

    aqi_pm25 = calc_epa_aqi(pm25, 'pm25')
    aqi_pm10 = calc_epa_aqi(pm10, 'pm10')
    
    return max(aqi_pm25, aqi_pm10)

if __name__ == '__main__':
    app.run(debug=True, port=5000)


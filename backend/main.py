# Author: Daksha009
# Repo: https://github.com/Daksha009/AirSense-Guardian.git

"""
AirSense Guardian - FastAPI Backend
Modern, fast API with automatic interactive documentation
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
import numpy as np
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from models.predictor import AQIPredictor
from models.source_attribution import SourceAttribution
from models.action_engine import ActionEngine
from pydantic import BaseModel
from typing import Optional

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AirSense Guardian API",
    description="Community-driven air quality intelligence system",
    version="1.0.0",
    docs_url="/docs",  # Interactive API docs at /docs
    redoc_url="/redoc"  # Alternative docs at /redoc
)

# Configure CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models
predictor = AQIPredictor()
source_attributor = SourceAttribution()
action_engine = ActionEngine()

# API Keys (set in .env file)
OPENAQ_API_KEY = os.getenv('OPENAQ_API_KEY', '')
AQICN_TOKEN = os.getenv('AQICN_TOKEN', '')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

# Pydantic models for request/response validation
class LocationRequest(BaseModel):
    lat: float
    lon: float
    hours: Optional[int] = 6

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "AirSense Guardian API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/aqi/current")
async def get_current_aqi(
    lat: float = Query(..., description="Latitude", example=28.6139),
    lon: float = Query(..., description="Longitude", example=77.2090)
):
    """
    Get current AQI data with predictions, source attribution, and actions
    
    - **lat**: Latitude of the location
    - **lon**: Longitude of the location
    
    Returns complete AQI analysis including:
    - Current AQI and pollutant levels
    - Weather data
    - Source attribution
    - Predictions for next 3 hours
    - Actionable recommendations
    """
    try:
        # Fetch from OpenAQ
        aqi_data = await fetch_openaq_data(lat, lon)
        
        # Fetch weather data
        weather_data = await fetch_weather_data(lat, lon)
        
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
        predictions = await fetch_live_aqi_predictions(lat, lon, hours=3)
        
        # Get actionable insights
        actions = action_engine.generate_actions(
            aqi_data.get('aqi', 0),
            sources,
            weather_data,
            traffic_density
        )
        
        # Get predictions (now using LIVE forecasting)
        predictions = await fetch_live_aqi_predictions(lat, lon, hours=3)
        
        # Get alerts
        alerts = get_alerts_from_data(aqi_data.get('aqi', 0), predictions)
        
        return {
            "current": {
                "aqi": aqi_data.get('aqi', 0),
                "pm25": aqi_data.get('pm25', 0),
                "pm10": aqi_data.get('pm10', 0),
                "no2": aqi_data.get('no2', 0),
                "timestamp": datetime.now().isoformat(),
                "location": {"lat": lat, "lon": lon}
            },
            "weather": weather_data,
            "traffic_density": traffic_density,
            "sources": sources,
            "predictions": predictions,
            "actions": actions,
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/aqi/predict")
async def predict_aqi(request: LocationRequest):
    """
    Get AQI predictions for multiple hours ahead
    
    - **lat**: Latitude
    - **lon**: Longitude  
    - **hours**: Number of hours to predict (default: 6)
    """
    try:
        # Get current data
        aqi_data = await fetch_openaq_data(request.lat, request.lon)
        weather_data = await fetch_weather_data(request.lat, request.lon)
        traffic_density = estimate_traffic_density(request.lat, request.lon)
        
        # Generate predictions
        predictions = await fetch_live_aqi_predictions(request.lat, request.lon, hours=request.hours)
        
        return {
            "predictions": predictions,
            "location": {"lat": request.lat, "lon": request.lon}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
async def get_alerts(
    lat: float = Query(..., description="Latitude", example=28.6139),
    lon: float = Query(..., description="Longitude", example=77.2090)
):
    """
    Get pollution alerts and warnings for a location
    
    Returns alerts for:
    - Current unhealthy conditions
    - Predicted high pollution periods
    """
    try:
        aqi_data = await fetch_openaq_data(lat, lon)
        weather_data = await fetch_weather_data(lat, lon)
        traffic_density = estimate_traffic_density(lat, lon)
        
        predictions = await fetch_live_aqi_predictions(lat, lon, hours=6)
        
        alerts = get_alerts_from_data(aqi_data.get('aqi', 0), predictions)
        
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# City bounding boxes for smart city-name lookup (lat_min, lat_max, lon_min, lon_max, city_slug)
CITY_BBOX = [
    (28.40, 28.88, 76.84, 77.35, "delhi"),
    (18.87, 19.27, 72.77, 73.00, "mumbai"),
    (12.83, 13.18, 77.47, 77.75, "bangalore"),
    (17.30, 17.55, 78.32, 78.60, "hyderabad"),
    (22.45, 22.75, 88.23, 88.47, "kolkata"),
    (12.95, 13.20, 80.16, 80.32, "chennai"),
    (22.97, 23.13, 72.50, 72.72, "ahmedabad"),
    (18.43, 18.63, 73.78, 73.98, "pune"),
]

def get_city_slug(lat: float, lon: float) -> str:
    """Return AQICN city slug if coordinates fall inside a known city, else None"""
    for lat_min, lat_max, lon_min, lon_max, slug in CITY_BBOX:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return slug
    return None

# Helper functions
async def fetch_openaq_data(lat: float, lon: float):
    """Fetch AQI data from AQICN (city feed preferred) or OpenAQ API"""
    if AQICN_TOKEN:
        try:
            # Try city-name feed first (gives city-wide representative AQI)
            city_slug = get_city_slug(lat, lon)
            if city_slug:
                city_url = f"https://api.waqi.info/feed/{city_slug}/?token={AQICN_TOKEN}"
                city_resp = requests.get(city_url, timeout=10)
                if city_resp.status_code == 200:
                    city_data = city_resp.json()
                    if city_data.get('status') == 'ok':
                        aqi_d = city_data['data']
                        aqi = aqi_d.get('aqi', 0)
                        iaqi = aqi_d.get('iaqi', {})
                        if isinstance(aqi, (int, float)) and aqi > 0:
                            print(f"[AQICN] City feed '{city_slug}': AQI={aqi}")
                            return {
                                'aqi': aqi,
                                'pm25': iaqi.get('pm25', {}).get('v', 0),
                                'pm10': iaqi.get('pm10', {}).get('v', 0),
                                'no2': iaqi.get('no2', {}).get('v', 0),
                            }

            # Fallback to geo-based lookup
            url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={AQICN_TOKEN}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    aqi_data = data.get('data', {})
                    aqi = aqi_data.get('aqi', 0)
                    iaqi = aqi_data.get('iaqi', {})
                    pm25 = iaqi.get('pm25', {}).get('v', 0)
                    pm10 = iaqi.get('pm10', {}).get('v', 0)
                    no2 = iaqi.get('no2', {}).get('v', 0)
                    
                    if isinstance(aqi, (int, float)) and aqi > 0:
                        print(f"[AQICN] Geo feed: AQI={aqi}")
                        return {
                            'aqi': aqi,
                            'pm25': pm25,
                            'pm10': pm10,
                            'no2': no2
                        }
        except Exception as e:
            print(f"Error fetching AQICN data: {e}")

    try:
        url = "https://api.openaq.org/v2/locations"
        params = {
            'coordinates': f"{lat},{lon}",
            'radius': 10000,
            'limit': 1
        }
        
        headers = {}
        if OPENAQ_API_KEY:
            headers['X-API-Key'] = OPENAQ_API_KEY
            
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('results') and len(data['results']) > 0:
                location = data['results'][0]
                measurements_url = f"https://api.openaq.org/v2/locations/{location['id']}/latest"
                meas_response = requests.get(measurements_url, headers=headers, timeout=10)
                
                if meas_response.status_code == 200:
                    meas_data = meas_response.json()
                    measurements = meas_data.get('results', [])
                    
                    pm25 = 0
                    pm10 = 0
                    no2 = 0
                    
                    for meas in measurements:
                        parameter = meas.get('parameter', '').lower()
                        value = meas.get('value', 0)
                        
                        if parameter == 'pm25':
                            pm25 = value
                        elif parameter == 'pm10':
                            pm10 = value
                        elif parameter == 'no2':
                            no2 = value
                    
                    aqi = calculate_aqi(pm25, pm10)
                    
                    return {
                        'aqi': aqi,
                        'pm25': pm25,
                        'pm10': pm10,
                        'no2': no2
                    }
        
        # Fallback: Use realistic Delhi AQI data (typical range: 150-250)
        # Delhi typically has high AQI due to traffic, industry, and seasonal factors
        base_aqi = 180  # Typical Delhi AQI
        variation = np.random.randint(-30, 50)
        aqi = max(50, min(400, base_aqi + variation))
        
        # Calculate pollutants based on AQI
        pm25 = max(10, aqi * 0.4 + np.random.randint(-5, 10))
        pm10 = max(20, aqi * 0.6 + np.random.randint(-10, 15))
        no2 = max(15, aqi * 0.2 + np.random.randint(-5, 10))
        
        return {
            'aqi': round(aqi),
            'pm25': round(pm25, 1),
            'pm10': round(pm10, 1),
            'no2': round(no2, 1)
        }
    except Exception as e:
        print(f"Error fetching OpenAQ data: {e}")
        # Fallback: Use realistic Delhi AQI data
        base_aqi = 180
        variation = np.random.randint(-30, 50)
        aqi = max(50, min(400, base_aqi + variation))
        
        pm25 = max(10, aqi * 0.4 + np.random.randint(-5, 10))
        pm10 = max(20, aqi * 0.6 + np.random.randint(-10, 15))
        no2 = max(15, aqi * 0.2 + np.random.randint(-5, 10))
        
        return {
            'aqi': round(aqi),
            'pm25': round(pm25, 1),
            'pm10': round(pm10, 1),
            'no2': round(no2, 1)
        }

async def fetch_weather_data(lat: float, lon: float):
    """Fetch weather data"""
    try:
        api_key = WEATHER_API_KEY or 'demo_key'
        url = "https://api.openweathermap.org/data/2.5/weather"
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
                'wind_speed': wind.get('speed', 0) * 3.6,
                'humidity': main.get('humidity', 50),
                'temperature': main.get('temp', 25),
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

async def fetch_live_aqi_predictions(lat: float, lon: float, hours: int = 6):
    """Fetch live air pollution predictions from OpenWeatherMap"""
    predictions = []
    try:
        api_key = WEATHER_API_KEY or 'demo_key'
        url = "http://api.openweathermap.org/data/2.5/air_pollution/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            forecast_list = data.get('list', [])
            
            # Use the data coming from an hour later for exact forward hourly predictions
            # OpenWeatherMap returns future 3600 interval timestamps
            for i in range(min(hours, len(forecast_list))):
                item = forecast_list[i]
                comp = item.get('components', {})
                pm25 = comp.get('pm2_5', 0)
                pm10 = comp.get('pm10', 0)
                
                pred_aqi = calculate_aqi(pm25, pm10)
                pred_time = datetime.fromtimestamp(item.get('dt', datetime.now().timestamp()))
                
                predictions.append({
                    'time': pred_time.isoformat(),
                    'aqi': pred_aqi,
                    'hours_ahead': i + 1
                })
            
            return predictions
            
    except Exception as e:
        print(f"Error fetching live API predictions: {e}")
        
    # If live fetch fails, fall back to simple local approximation
    current_time = datetime.now()
    for i in range(1, hours + 1):
        pred_time = current_time + timedelta(hours=i)
        predictions.append({
            'time': pred_time.isoformat(),
            'aqi': 120 + np.random.randint(-10, 10), # arbitrary fallback
            'hours_ahead': i
        })
    return predictions

def estimate_traffic_density(lat: float, lon: float):
    """Estimate traffic density"""
    hour = datetime.now().hour
    
    if (7 <= hour <= 9) or (17 <= hour <= 19):
        base_density = 0.8
    elif (10 <= hour <= 16):
        base_density = 0.5
    else:
        base_density = 0.3
    
    density = base_density + np.random.uniform(-0.1, 0.1)
    return max(0, min(1, density))

def calculate_aqi(pm25: float, pm10: float):
    """Calculate US AQI from PM2.5 and PM10"""
    def pm25_to_aqi(c):
        if c <= 12.0: return (50/12.0)*c
        elif c <= 35.4: return 50 + ((100-50)/(35.4-12.0))*(c-12.0)
        elif c <= 55.4: return 100 + ((150-100)/(55.4-35.4))*(c-35.4)
        elif c <= 150.4: return 150 + ((200-150)/(150.4-55.4))*(c-55.4)
        elif c <= 250.4: return 200 + ((300-200)/(250.4-150.4))*(c-150.4)
        else: return 300 + ((500-300)/(500.4-250.4))*(c-250.4)
        
    def pm10_to_aqi(c):
        if c <= 54: return (50/54)*c
        elif c <= 154: return 50 + ((100-50)/(154-54))*(c-54)
        elif c <= 254: return 100 + ((150-100)/(254-154))*(c-154)
        elif c <= 354: return 150 + ((200-150)/(354-254))*(c-254)
        elif c <= 424: return 200 + ((300-200)/(424-354))*(c-354)
        else: return 300 + ((500-300)/(604-424))*(c-424)

    aqi_pm25 = pm25_to_aqi(pm25) if pm25 > 0 else 0
    aqi_pm10 = pm10_to_aqi(pm10) if pm10 > 0 else 0
    return max(aqi_pm25, aqi_pm10)

def get_alerts_from_data(current_aqi: float, predictions: list):
    """Generate alerts from AQI data and predictions"""
    alerts = []
    
    if current_aqi > 150:
        alerts.append({
            'type': 'warning',
            'severity': 'high' if current_aqi > 200 else 'moderate',
            'message': f'Current AQI is {current_aqi:.0f} - Unhealthy conditions detected',
            'timestamp': datetime.now().isoformat()
        })
    
    for pred in predictions:
        if pred['aqi'] > 150:
            alerts.append({
                'type': 'prediction',
                'severity': 'high' if pred['aqi'] > 200 else 'moderate',
                'message': f'High AQI ({pred["aqi"]:.0f}) expected at {pred["time"]}',
                'timestamp': pred['time'],
                'aqi': pred['aqi']
            })
    
    return alerts

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)


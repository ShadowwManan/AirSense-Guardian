"""
AirSense Guardian - FastAPI Backend (Vercel Serverless)
"""
import sys
import os

# Ensure api/models is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from models.predictor import AQIPredictor
from models.source_attribution import SourceAttribution
from models.action_engine import ActionEngine
from pydantic import BaseModel
from typing import Optional

# Load .env from backend directory (for local dev), or rely on Vercel env vars
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(dotenv_path)

app = FastAPI(
    title="AirSense Guardian API",
    description="Community-driven air quality intelligence system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

predictor = AQIPredictor()
source_attributor = SourceAttribution()
action_engine = ActionEngine()

OPENAQ_API_KEY = os.getenv('OPENAQ_API_KEY', '')
AQICN_TOKEN = os.getenv('AQICN_TOKEN', '')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')


class LocationRequest(BaseModel):
    lat: float
    lon: float
    hours: Optional[int] = 6


@app.get("/api")
async def root():
    return {"message": "AirSense Guardian API", "version": "1.0.0", "status": "running"}


@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


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
    for lat_min, lat_max, lon_min, lon_max, slug in CITY_BBOX:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return slug
    return None


@app.get("/api/aqi/current")
async def get_current_aqi(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
):
    try:
        aqi_data = await fetch_openaq_data(lat, lon)
        weather_data = await fetch_weather_data(lat, lon)
        traffic_density = estimate_traffic_density(lat, lon)

        sources = source_attributor.attribute_sources(
            aqi_data.get('aqi', 0),
            weather_data.get('wind_speed', 0),
            traffic_density,
            datetime.now().hour
        )

        predictions = await fetch_live_aqi_predictions(lat, lon, hours=3)

        actions = action_engine.generate_actions(
            aqi_data.get('aqi', 0),
            sources,
            weather_data,
            traffic_density
        )

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
    try:
        predictions = await fetch_live_aqi_predictions(request.lat, request.lon, hours=request.hours)
        return {"predictions": predictions, "location": {"lat": request.lat, "lon": request.lon}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts")
async def get_alerts(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
):
    try:
        aqi_data = await fetch_openaq_data(lat, lon)
        predictions = await fetch_live_aqi_predictions(lat, lon, hours=6)
        alerts = get_alerts_from_data(aqi_data.get('aqi', 0), predictions)
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def fetch_openaq_data(lat: float, lon: float):
    if AQICN_TOKEN:
        try:
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
                            return {
                                'aqi': aqi,
                                'pm25': iaqi.get('pm25', {}).get('v', 0),
                                'pm10': iaqi.get('pm10', {}).get('v', 0),
                                'no2': iaqi.get('no2', {}).get('v', 0),
                            }

            url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={AQICN_TOKEN}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    aqi_data = data.get('data', {})
                    aqi = aqi_data.get('aqi', 0)
                    iaqi = aqi_data.get('iaqi', {})
                    if isinstance(aqi, (int, float)) and aqi > 0:
                        return {
                            'aqi': aqi,
                            'pm25': iaqi.get('pm25', {}).get('v', 0),
                            'pm10': iaqi.get('pm10', {}).get('v', 0),
                            'no2': iaqi.get('no2', {}).get('v', 0)
                        }
        except Exception as e:
            print(f"Error fetching AQICN data: {e}")

    base_aqi = 180
    variation = np.random.randint(-30, 50)
    aqi = max(50, min(400, base_aqi + variation))
    pm25 = max(10, aqi * 0.4 + np.random.randint(-5, 10))
    pm10 = max(20, aqi * 0.6 + np.random.randint(-10, 15))
    no2 = max(15, aqi * 0.2 + np.random.randint(-5, 10))
    return {'aqi': round(aqi), 'pm25': round(pm25, 1), 'pm10': round(pm10, 1), 'no2': round(no2, 1)}


async def fetch_weather_data(lat: float, lon: float):
    try:
        api_key = WEATHER_API_KEY or 'demo_key'
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric'}
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
    except Exception as e:
        print(f"Error fetching weather: {e}")

    return {
        'wind_speed': round(8 + np.random.randint(-2, 5), 1),
        'humidity': 55 + np.random.randint(-15, 20),
        'temperature': round(28 + np.random.randint(-5, 8), 1),
        'pressure': 1010 + np.random.randint(-5, 5)
    }


async def fetch_live_aqi_predictions(lat: float, lon: float, hours: int = 6):
    predictions = []
    try:
        api_key = WEATHER_API_KEY or 'demo_key'
        url = "http://api.openweathermap.org/data/2.5/air_pollution/forecast"
        params = {'lat': lat, 'lon': lon, 'appid': api_key}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            forecast_list = data.get('list', [])
            for i in range(min(hours, len(forecast_list))):
                item = forecast_list[i]
                comp = item.get('components', {})
                pm25 = comp.get('pm2_5', 0)
                pm10 = comp.get('pm10', 0)
                pred_aqi = calculate_aqi(pm25, pm10)
                pred_time = datetime.fromtimestamp(item.get('dt', datetime.now().timestamp()))
                predictions.append({'time': pred_time.isoformat(), 'aqi': pred_aqi, 'hours_ahead': i + 1})
            return predictions
    except Exception as e:
        print(f"Error fetching live predictions: {e}")

    current_time = datetime.now()
    for i in range(1, hours + 1):
        pred_time = current_time + timedelta(hours=i)
        predictions.append({'time': pred_time.isoformat(), 'aqi': 120 + np.random.randint(-10, 10), 'hours_ahead': i})
    return predictions


def estimate_traffic_density(lat: float, lon: float):
    hour = datetime.now().hour
    if (7 <= hour <= 9) or (17 <= hour <= 19):
        base_density = 0.8
    elif 10 <= hour <= 16:
        base_density = 0.5
    else:
        base_density = 0.3
    return max(0, min(1, base_density + np.random.uniform(-0.1, 0.1)))


def calculate_aqi(pm25: float, pm10: float):
    def pm25_to_aqi(c):
        if c <= 12.0: return (50 / 12.0) * c
        elif c <= 35.4: return 50 + ((100 - 50) / (35.4 - 12.0)) * (c - 12.0)
        elif c <= 55.4: return 100 + ((150 - 100) / (55.4 - 35.4)) * (c - 35.4)
        elif c <= 150.4: return 150 + ((200 - 150) / (150.4 - 55.4)) * (c - 55.4)
        elif c <= 250.4: return 200 + ((300 - 200) / (250.4 - 150.4)) * (c - 150.4)
        else: return 300 + ((500 - 300) / (500.4 - 250.4)) * (c - 250.4)

    def pm10_to_aqi(c):
        if c <= 54: return (50 / 54) * c
        elif c <= 154: return 50 + ((100 - 50) / (154 - 54)) * (c - 54)
        elif c <= 254: return 100 + ((150 - 100) / (254 - 154)) * (c - 154)
        elif c <= 354: return 150 + ((200 - 150) / (354 - 254)) * (c - 254)
        elif c <= 424: return 200 + ((300 - 200) / (424 - 354)) * (c - 354)
        else: return 300 + ((500 - 300) / (604 - 424)) * (c - 424)

    aqi_pm25 = pm25_to_aqi(pm25) if pm25 > 0 else 0
    aqi_pm10 = pm10_to_aqi(pm10) if pm10 > 0 else 0
    return max(aqi_pm25, aqi_pm10)


def get_alerts_from_data(current_aqi: float, predictions: list):
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
    uvicorn.run("index:app", host="0.0.0.0", port=5000, reload=True)

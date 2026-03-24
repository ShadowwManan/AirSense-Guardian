import os
import requests
from dotenv import load_dotenv

load_dotenv()

AQICN_TOKEN = os.getenv('AQICN_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

LAT, LON = 28.6139, 77.2090

def test_aqicn():
    if not AQICN_TOKEN:
        print("[-] AQICN_TOKEN not found in .env")
        return
    
    print(f"Testing AQICN API with token: {AQICN_TOKEN[:5]}...{AQICN_TOKEN[-5:]}")
    url = f"https://api.waqi.info/feed/geo:{LAT};{LON}/?token={AQICN_TOKEN}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('status') == 'ok':
            print("[+] AQICN API is WORKING")
            print(f"    Current AQI in Delhi: {data['data']['aqi']}")
        else:
            print(f"[-] AQICN API returned error: {data.get('data')}")
    except Exception as e:
        print(f"[-] AQICN API request failed: {e}")

def test_owm():
    if not WEATHER_API_KEY:
        print("[-] WEATHER_API_KEY not found in .env")
        return
    
    print(f"Testing OpenWeatherMap API with key: {WEATHER_API_KEY[:5]}...{WEATHER_API_KEY[-5:]}")
    url = f"http://api.openweathermap.org/data/2.5/air_pollution"
    params = {'lat': LAT, 'lon': LON, 'appid': WEATHER_API_KEY}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("[+] OpenWeatherMap API is WORKING")
            if data.get('list'):
                print(f"    AQI Index (OWM): {data['list'][0]['main']['aqi']}")
        else:
            print(f"[-] OpenWeatherMap API returned status code: {response.status_code}")
            print(f"    Message: {response.text}")
    except Exception as e:
        print(f"[-] OpenWeatherMap API request failed: {e}")

if __name__ == "__main__":
    print("--- API Key Verification ---")
    test_aqicn()
    print("-" * 30)
    test_owm()

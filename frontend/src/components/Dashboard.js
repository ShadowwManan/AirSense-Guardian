/*
 * Author: Daksha009
 * Repo: https://github.com/Daksha009/AirSense-Guardian.git
 */
import React, { useState, useEffect } from 'react';
import AOS from 'aos';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const cityCoordinates = {
  'delhi': { lat: 28.6139, lon: 77.2090, name: 'New Delhi', state: 'Delhi' },
  'mumbai': { lat: 19.0760, lon: 72.8777, name: 'Mumbai', state: 'Maharashtra' },
  'bangalore': { lat: 12.9716, lon: 77.5946, name: 'Bangalore', state: 'Karnataka' },
  'kolkata': { lat: 22.5726, lon: 88.3639, name: 'Kolkata', state: 'West Bengal' },
  'chennai': { lat: 13.0827, lon: 80.2707, name: 'Chennai', state: 'Tamil Nadu' },
  'hyderabad': { lat: 17.3850, lon: 78.4867, name: 'Hyderabad', state: 'Telangana' },
  'pune': { lat: 18.5204, lon: 73.8567, name: 'Pune', state: 'Maharashtra' },
  'ahmedabad': { lat: 23.0225, lon: 72.5714, name: 'Ahmedabad', state: 'Gujarat' },
  'surat': { lat: 21.1702, lon: 72.8311, name: 'Surat', state: 'Gujarat' },
  'jaipur': { lat: 26.9124, lon: 75.7873, name: 'Jaipur', state: 'Rajasthan' },
  'lucknow': { lat: 26.8467, lon: 80.9462, name: 'Lucknow', state: 'Uttar Pradesh' },
  'kanpur': { lat: 26.4499, lon: 80.3319, name: 'Kanpur', state: 'Uttar Pradesh' },
  'nagpur': { lat: 21.1458, lon: 79.0882, name: 'Nagpur', state: 'Maharashtra' },
  'indore': { lat: 22.7196, lon: 75.8577, name: 'Indore', state: 'Madhya Pradesh' },
  'thane': { lat: 19.2183, lon: 72.9781, name: 'Thane', state: 'Maharashtra' },
  'bhopal': { lat: 23.2599, lon: 77.4126, name: 'Bhopal', state: 'Madhya Pradesh' },
  'visakhapatnam': { lat: 17.6868, lon: 83.2185, name: 'Visakhapatnam', state: 'Andhra Pradesh' },
  'patna': { lat: 25.5941, lon: 85.1376, name: 'Patna', state: 'Bihar' },
  'vadodara': { lat: 22.3072, lon: 73.1812, name: 'Vadodara', state: 'Gujarat' },
  'ghaziabad': { lat: 28.6692, lon: 77.4538, name: 'Ghaziabad', state: 'Uttar Pradesh' },
  'ludhiana': { lat: 30.9010, lon: 75.8573, name: 'Ludhiana', state: 'Punjab' },
  'agra': { lat: 27.1767, lon: 78.0081, name: 'Agra', state: 'Uttar Pradesh' },
  'nashik': { lat: 19.9975, lon: 73.7898, name: 'Nashik', state: 'Maharashtra' },
  'faridabad': { lat: 28.4089, lon: 77.3178, name: 'Faridabad', state: 'Haryana' },
  'meerut': { lat: 28.9845, lon: 77.7064, name: 'Meerut', state: 'Uttar Pradesh' },
  'rajkot': { lat: 22.3039, lon: 70.8022, name: 'Rajkot', state: 'Gujarat' },
  'varanasi': { lat: 25.3176, lon: 82.9739, name: 'Varanasi', state: 'Uttar Pradesh' },
  'srinagar': { lat: 34.0837, lon: 74.7973, name: 'Srinagar', state: 'Jammu and Kashmir' },
  'amritsar': { lat: 31.6340, lon: 74.8723, name: 'Amritsar', state: 'Punjab' },
  'chandigarh': { lat: 30.7333, lon: 76.7794, name: 'Chandigarh', state: 'Chandigarh' }
};

const stateCapitals = {
  'delhi': { lat: 28.6139, lon: 77.2090, name: 'Delhi', capital: 'New Delhi' },
  'maharashtra': { lat: 19.0760, lon: 72.8777, name: 'Maharashtra', capital: 'Mumbai' },
  'karnataka': { lat: 12.9716, lon: 77.5946, name: 'Karnataka', capital: 'Bangalore' },
  'west bengal': { lat: 22.5726, lon: 88.3639, name: 'West Bengal', capital: 'Kolkata' },
  'tamil nadu': { lat: 13.0827, lon: 80.2707, name: 'Tamil Nadu', capital: 'Chennai' },
  'telangana': { lat: 17.3850, lon: 78.4867, name: 'Telangana', capital: 'Hyderabad' },
  'gujarat': { lat: 23.0225, lon: 72.5714, name: 'Gujarat', capital: 'Ahmedabad' },
  'rajasthan': { lat: 26.9124, lon: 75.7873, name: 'Rajasthan', capital: 'Jaipur' },
  'uttar pradesh': { lat: 26.8467, lon: 80.9462, name: 'Uttar Pradesh', capital: 'Lucknow' },
  'punjab': { lat: 30.7333, lon: 76.7794, name: 'Punjab', capital: 'Chandigarh' },
  'madhya pradesh': { lat: 23.2599, lon: 77.4126, name: 'Madhya Pradesh', capital: 'Bhopal' },
  'andhra pradesh': { lat: 17.6868, lon: 83.2185, name: 'Andhra Pradesh', capital: 'Visakhapatnam' },
  'bihar': { lat: 25.5941, lon: 85.1376, name: 'Bihar', capital: 'Patna' },
  'haryana': { lat: 28.4089, lon: 77.3178, name: 'Haryana', capital: 'Chandigarh' },
  'jammu and kashmir': { lat: 34.0837, lon: 74.7973, name: 'Jammu and Kashmir', capital: 'Srinagar' },
  'chandigarh': { lat: 30.7333, lon: 76.7794, name: 'Chandigarh', capital: 'Chandigarh' }
};

const Dashboard = ({ onDataUpdate }) => {
  const [searchType, setSearchType] = useState('city');
  const [searchInput, setSearchInput] = useState('');
  const [aqiData, setAqiData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cityName, setCityName] = useState('New Delhi');

  useEffect(() => {
    AOS.init({ duration: 800, once: true });
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setTimeout(async () => {
      const data = await fetchAQIData(28.6139, 77.2090);
      if (data) {
        setAqiData(data);
        setCityName('New Delhi');
        if (onDataUpdate) onDataUpdate(data);
      }
    }, 1000);
  };

  const fetchAQIData = async (lat, lon) => {
    try {
      const url = `${API_BASE_URL}/aqi/current?lat=${lat}&lon=${lon}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        mode: 'cors',
        cache: 'no-cache'
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching AQI data:', error);
      return null;
    }
  };

  const handleSearch = async (overrideInput = null) => {
    const input = (overrideInput || searchInput).trim().toLowerCase();
    if (!input) return;

    setLoading(true);
    let coords = null;
    let displayName = '';

    if (searchType === 'city') {
      coords = cityCoordinates[input];
      if (!coords) {
        for (const [key, value] of Object.entries(cityCoordinates)) {
          if (key.includes(input) || value.name.toLowerCase().includes(input)) {
            coords = value;
            break;
          }
        }
      }
      if (coords) displayName = coords.name;
    } else {
      const stateKey = input.replace(/\s+/g, ' ').toLowerCase();
      coords = stateCapitals[stateKey];
      if (!coords) {
        for (const [key, value] of Object.entries(stateCapitals)) {
          if (key.includes(input) || value.name.toLowerCase().includes(input)) {
            coords = value;
            break;
          }
        }
      }
      if (coords) displayName = `${coords.capital}, ${coords.name}`;
    }

    if (!coords) {
      alert(`${searchType === 'city' ? 'City' : 'State'} not found. Please try a different name.`);
      setLoading(false);
      return;
    }

    const data = await fetchAQIData(coords.lat, coords.lon);
    if (data) {
      setAqiData(data);
      setCityName(displayName);
      if (onDataUpdate) onDataUpdate(data);
    } else {
      alert('Failed to fetch data. Make sure backend is running.');
    }
    setLoading(false);
  };

  const selectState = (stateName) => {
    setSearchInput(stateName);
    handleSearch(stateName);
  };

  const getAQIStatus = (aqi) => {
    if (aqi > 300) return { text: 'Hazardous', color: 'red' };
    if (aqi > 200) return { text: 'Very Unhealthy', color: 'red' };
    if (aqi > 150) return { text: 'Unhealthy', color: 'red' };
    if (aqi > 100) return { text: 'Unhealthy Sensitive', color: 'orange' };
    if (aqi > 50) return { text: 'Moderate', color: 'yellow' };
    return { text: 'Good', color: 'green' };
  };

  const aqi = aqiData?.current?.aqi ? Math.round(aqiData.current.aqi) : 134;
  const status = getAQIStatus(aqi);
  const pm25 = aqiData?.current?.pm25 ? Math.round(aqiData.current.pm25) : 45;
  const pm10 = aqiData?.current?.pm10 ? Math.round(aqiData.current.pm10) : 82;
  const temp = aqiData?.weather?.temperature ? Math.round(aqiData.weather.temperature) : 28;

  return (
    <section id="dashboard" className="py-20 px-4 relative z-10">
      <div className="max-w-7xl mx-auto">
        <div className="relative max-w-2xl mx-auto mb-16" data-aos="fade-up">
          <div className="flex flex-col gap-4">
            <div className="flex gap-2 justify-center">
              <button
                onClick={() => setSearchType('city')}
                className={`px-4 py-2 font-bold rounded-lg transition-colors ${searchType === 'city'
                  ? 'bg-brand-green text-white hover:bg-[#3d8b50]'
                  : 'glass-card hover:bg-white/10 font-medium text-white'
                  }`}
              >
                <i className="fas fa-city mr-2"></i>City
              </button>
              <button
                onClick={() => setSearchType('state')}
                className={`px-4 py-2 font-bold rounded-lg transition-colors ${searchType === 'state'
                  ? 'bg-brand-green text-white hover:bg-[#3d8b50]'
                  : 'glass-card hover:bg-white/10 font-medium text-white'
                  }`}
              >
                <i className="fas fa-map mr-2"></i>State
              </button>
            </div>

            <div className="flex items-center bg-[#0e110f] border border-brand-green/30 rounded-2xl p-2 shadow-[0_0_30px_rgba(73,167,96,0.1)]">
              <i className="fas fa-search text-brand-green ml-4 text-xl"></i>
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder={searchType === 'city' ? 'Enter City Name (e.g. Delhi, Mumbai)' : 'Enter State Name (e.g. Maharashtra, Karnataka)'}
                className="w-full bg-transparent border-none text-white text-lg px-4 py-3 focus:ring-0 placeholder-gray-500 outline-none"
              />
              <button
                onClick={handleSearch}
                disabled={loading}
                className="bg-brand-green text-white font-bold px-6 py-3 rounded-xl hover:bg-[#3d8b50] transition-colors disabled:opacity-50"
              >
                {loading ? '...' : 'Analyze'}
              </button>
            </div>

            {searchType === 'state' && (
              <div className="flex flex-wrap gap-2 justify-center">
                {['Delhi', 'Maharashtra', 'Karnataka', 'West Bengal', 'Tamil Nadu', 'Telangana', 'Gujarat', 'Rajasthan', 'Uttar Pradesh', 'Punjab'].map((state) => (
                  <button
                    key={state}
                    onClick={() => selectState(state)}
                    className="px-3 py-1 glass-card hover:bg-brand-green/20 text-sm text-gray-300 rounded-lg transition-colors"
                  >
                    {state}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2 glass-card p-10 relative overflow-hidden group" data-aos="fade-right">
            <div className="absolute right-[-20px] top-[-20px] w-64 h-64 bg-brand-green/10 blur-[80px] rounded-full group-hover:bg-brand-green/20 transition-all"></div>

            <div className="flex justify-between items-start mb-8">
              <div>
                <h2 id="cityName" className="text-4xl font-display font-bold mb-1">{cityName}</h2>
                <p className="text-sm text-brand-accent flex items-center gap-2">
                  <span className="w-2 h-2 bg-brand-accent rounded-full animate-pulse"></span> Live Sensors
                </p>
              </div>
              <div className={`px-5 py-2 rounded-lg font-bold text-sm tracking-wider uppercase ${status.color === 'red' ? 'bg-red-500/10 border border-red-500/40 text-red-400' :
                status.color === 'orange' ? 'bg-orange-500/10 border border-orange-500/40 text-orange-400' :
                  status.color === 'yellow' ? 'bg-yellow-500/10 border border-yellow-500/40 text-yellow-400' :
                    'bg-green-500/10 border border-green-500/40 text-green-400'
                }`}>
                {status.text}
              </div>
            </div>

            <div className="flex items-baseline gap-4 mb-4">
              <span id="aqiValue" className="text-9xl font-display font-bold text-white tracking-tighter leading-none">{loading ? '...' : aqi}</span>
              <div className="flex flex-col">
                <span className="text-xl text-gray-400">AQI</span>
                <span className="text-xs text-gray-500">PM2.5 Dominant</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div className="glass-card p-6 flex items-center justify-between hover:bg-white/5 transition-colors" data-aos="fade-left" data-aos-delay="100">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-500/10 rounded-lg text-blue-400"><i className="fas fa-wind"></i></div>
                <span className="text-gray-300">PM2.5</span>
              </div>
              <span className="font-bold text-2xl">{pm25}</span>
            </div>
            <div className="glass-card p-6 flex items-center justify-between hover:bg-white/5 transition-colors" data-aos="fade-left" data-aos-delay="200">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-purple-500/10 rounded-lg text-purple-400"><i className="fas fa-smog"></i></div>
                <span className="text-gray-300">PM10</span>
              </div>
              <span className="font-bold text-2xl">{pm10}</span>
            </div>
            <div className="glass-card p-6 flex items-center justify-between hover:bg-white/5 transition-colors" data-aos="fade-left" data-aos-delay="300">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-orange-500/10 rounded-lg text-orange-400"><i className="fas fa-temperature-half"></i></div>
                <span className="text-gray-300">Temp</span>
              </div>
              <span className="font-bold text-2xl">{temp}°C</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Dashboard;

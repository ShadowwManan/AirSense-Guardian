# Author: Daksha009
# Repo: https://github.com/Daksha009/AirSense-Guardian.git

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
import pickle
import os
import json

class AQIPredictor:
    def __init__(self):
        self.model = None
        self.feature_cols = None
        self.metadata = None
        # Model path - save in backend/models directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(script_dir, 'aqi_model.pkl')
        self.metadata_path = os.path.join(script_dir, 'model_metadata.json')
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize or load the prediction model"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                
                # Load metadata if available
                if os.path.exists(self.metadata_path):
                    with open(self.metadata_path, 'r') as f:
                        self.metadata = json.load(f)
                        self.feature_cols = self.metadata.get('feature_columns', None)
                
                print("Loaded trained model from file")
            except Exception as e:
                print(f"Error loading model: {e}. Creating new model...")
                self.model = self._create_model()
                self._train_model()
        else:
            print("No trained model found. Creating model with synthetic data...")
            self.model = self._create_model()
            self._train_model()
    
    def _create_model(self):
        """Create a new Random Forest model"""
        return RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )

    def _train_model(self):
        """Attempt to train with real data, fallback to synthetic."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(script_dir, '..', 'data', 'aqi_training_data.csv')
        
        trained_with_real = False
        if os.path.exists(data_path) and os.path.getsize(data_path) > 100:
            try:
                df = pd.read_csv(data_path)
                if len(df) > 10 and 'aqi' in df.columns:
                    print(f"Training model with real dataset ({len(df)} rows)...")
                    # Calculate target delta
                    df['aqi_next'] = df['aqi'].shift(-1)
                    
                    # Create lag features
                    df['lag1'] = df['aqi'].shift(1)
                    df['lag2'] = df['aqi'].shift(2)
                    df['lag3'] = df['aqi'].shift(3)
                    df['rolling_3'] = df['aqi'].rolling(3).mean()
                    df['rolling_6'] = df['aqi'].rolling(6).mean()
                    
                    df = df.dropna()
                    
                    X_real = []
                    y_real = []
                    
                    for _, row in df.iterrows():
                        timestamp = row.get('timestamp')
                        dt = pd.to_datetime(timestamp) if pd.notna(timestamp) else datetime.now()
                        
                        wind = row.get('wind_speed', 10.0) if 'wind_speed' in row else 10.0
                        hum = row.get('humidity', 50.0) if 'humidity' in row else 50.0
                        temp = row.get('temperature', 25.0) if 'temperature' in row else 25.0
                        
                        hour_sin = np.sin(2 * np.pi * dt.hour / 24)
                        hour_cos = np.cos(2 * np.pi * dt.hour / 24)
                        month_sin = np.sin(2 * np.pi * dt.month / 12)
                        month_cos = np.cos(2 * np.pi * dt.month / 12)
                        
                        stagnation = (hum / 100.0) * (1.0 - min(wind, 40) / 40.0)
                        
                        features = [
                            float(row['aqi']), float(row['lag1']), float(row['lag2']), float(row['lag3']),
                            float(row['rolling_3']), float(row['rolling_6']),
                            float(hour_sin), float(hour_cos), float(month_sin), float(month_cos),
                            float(wind), float(hum), float(temp), float(stagnation)
                        ]
                        
                        X_real.append(features)
                        y_real.append(float(row['aqi_next'] - row['aqi']))
                    
                    self.model.fit(np.array(X_real), np.array(y_real))
                    trained_with_real = True
                    print("Successfully trained with real CSV data!")
                    
                    # Save model and metadata
                    os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                    with open(self.model_path, 'wb') as f:
                        pickle.dump(self.model, f)
            except Exception as e:
                print(f"Could not train with real data: {e}")
                
        if not trained_with_real:
            print("Falling back to synthetic data training...")
            self._train_with_synthetic_data()
    
    def _train_with_synthetic_data(self):
        """Train model with advanced non-linear cyclical patterns (v3)"""
        np.random.seed(42)
        n_samples = 5000
        
        # Features: aqi(0), lags(1-3), rolling(4-5), hour_sin(6), hour_cos(7), month_sin(8), month_cos(9), wind(10), hum(11), temp(12), stagnation(13)
        X = np.random.rand(n_samples, 14)
        
        # Scales
        X[:, 0] = X[:, 0] * 450   # current_aqi
        X[:, 1] = X[:, 0] * 0.99  # lag1
        X[:, 2] = X[:, 0] * 0.97  # lag2
        X[:, 3] = X[:, 0] * 0.95  # lag3
        X[:, 10] = X[:, 10] * 35  # wind
        X[:, 11] = X[:, 11] * 100 # humidity
        X[:, 12] = X[:, 12] * 45  # temp
        
        # Cyclical Time (Hour 0-23, Month 1-12)
        hours = np.random.randint(0, 24, n_samples)
        X[:, 6] = np.sin(2 * np.pi * hours / 24)
        X[:, 7] = np.cos(2 * np.pi * hours / 24)
        
        months = np.random.randint(1, 13, n_samples)
        X[:, 8] = np.sin(2 * np.pi * months / 12)
        X[:, 9] = np.cos(2 * np.pi * months / 12)
        
        # Stagnation Index: High humidity + Low wind
        # Normalized: (hum/100) * (1 - wind/40)
        X[:, 13] = (X[:, 11]/100.0) * (1.0 - X[:, 10]/40.0)

        # TARGET: Delta logic with environmental physics
        y_delta = np.zeros(n_samples)
        for i in range(n_samples):
            # 1. Physics: Dispersion vs Accumulation
            # High wind + Low stagnation = Strong Drop
            dispersion = (X[i, 10] ** 1.3) * -0.6
            accumulation = (X[i, 13] * 50) 
            
            # 2. Daily Traffic Cycle (using actual hours)
            h = hours[i]
            traffic = 35 if (8 <= h <= 10 or 17 <= h <= 19) else 5
            
            # 3. Monthly seasonality (Pollution higher in Winter months: 10, 11, 12, 1)
            m = months[i]
            seasonal_multiplier = 1.5 if m in [10, 11, 12, 1] else 0.8
            
            # 4. Reversion to Mean (Negative Feedback)
            # If AQI is already huge (>350), it's more likely to drop unless trapped
            reversion = (200 - X[i, 0]) * 0.08
            
            delta = reversion + dispersion + (accumulation * seasonal_multiplier) + (traffic * seasonal_multiplier)
            y_delta[i] = (delta * 0.5) + np.random.normal(0, 2)

        # Train advanced model
        self.model.fit(X, y_delta)
        
        # Save model and metadata
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
            
        metadata = {
            'feature_columns': [
                'aqi', 'aqi_lag1', 'aqi_lag2', 'aqi_lag3', 
                'aqi_rolling_mean_3h', 'aqi_rolling_mean_6h',
                'hour_sin', 'hour_cos', 'month_sin', 'month_cos',
                'wind_speed', 'humidity', 'temperature', 'stagnation_index'
            ],
            'last_trained': datetime.now().isoformat(),
            'model_type': 'DeltaRegressor_Premium_v3'
        }
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f)

    def _prepare_features(self, current_aqi, wind_speed, humidity, traffic_density, current_time, 
                         aqi_history=None, temperature=25):
        """
        Prepare 14 advanced features with Cyclical Encoding
        """
        hour = current_time.hour
        month = current_time.month
        
        # Cyclical Encoding
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        month_sin = np.sin(2 * np.pi * month / 12)
        month_cos = np.cos(2 * np.pi * month / 12)
        
        # Stagnation Index (0-1)
        stagnation = (humidity/100.0) * (1.0 - min(wind_speed, 40)/40.0)
        
        # History
        hist = aqi_history if aqi_history and len(aqi_history) >= 6 else [current_aqi] * 6
        
        features = [
            float(current_aqi),
            float(hist[-1]), # lag1
            float(hist[-2]), # lag2
            float(hist[-3]), # lag3
            float(np.mean(hist[-3:])), 
            float(np.mean(hist[-6:])),
            float(hour_sin),
            float(hour_cos),
            float(month_sin),
            float(month_cos),
            float(wind_speed),
            float(humidity),
            float(temperature),
            float(stagnation)
        ]
        
        return np.array([features])
    
    def predict(self, current_aqi, wind_speed, humidity, traffic_density, current_time, aqi_history=None, temperature=25):
        """Predict AQI for next 3 hours using Delta-Logic"""
        predictions = []
        current_aqi_val = current_aqi
        
        for i in range(1, 4):
            # Prepare features
            features = self._prepare_features(
                current_aqi_val, wind_speed, humidity, traffic_density, 
                current_time + timedelta(hours=i-1), aqi_history, temperature
            )
            
            # Predict the DELTA
            delta = self.model.predict(features)[0]
            
            # DAMPEN the delta to prevent wild swings away from real live AQI
            # Max 15% change per hour
            max_delta = max(10, current_aqi_val * 0.15)
            delta = np.clip(delta, -max_delta, max_delta)
            
            # Calculate next AQI
            next_aqi = current_aqi_val + delta
            next_aqi = float(np.clip(next_aqi, 0, 500))
            
            pred_time = current_time + timedelta(hours=i)
            
            predictions.append({
                'time': pred_time.isoformat(),
                'aqi': next_aqi,
                'hours_ahead': i
            })
            
            # Update for next prediction
            current_aqi_val = next_aqi
            if aqi_history is not None:
                aqi_history = list(aqi_history) + [next_aqi]
        
        return predictions
    
    def predict_multiple_hours(self, current_aqi, wind_speed, humidity, traffic_density, current_time, hours=6, aqi_history=None, temperature=25):
        """Predict AQI for multiple hours ahead using Delta-Logic"""
        predictions = []
        current_aqi_val = current_aqi
        
        for i in range(1, hours + 1):
            # Prepare features
            features = self._prepare_features(
                current_aqi_val, wind_speed, humidity, traffic_density,
                current_time + timedelta(hours=i-1), aqi_history, temperature
            )
            
            # Predict the DELTA
            delta = self.model.predict(features)[0]
            
            # Calculate next AQI
            next_aqi = current_aqi_val + delta
            next_aqi = float(np.clip(next_aqi, 0, 500))
            
            pred_time = current_time + timedelta(hours=i)
            
            predictions.append({
                'time': pred_time.isoformat(),
                'aqi': next_aqi,
                'hours_ahead': i
            })
            
            # Use predicted AQI for next prediction
            current_aqi_val = next_aqi
            if aqi_history is not None:
                aqi_history = list(aqi_history) + [next_aqi]
        
        return predictions

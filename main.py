from datetime import datetime

import pytz
from flask import Flask, jsonify, request
import requests
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry
from flask_cors import CORS
requests_cache.clear()


app = Flask(__name__)

CORS(app)
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)
POWER_CAPACITY = 2.5
EFFICIENCY = 0.2
def calculate_solar_energy(sunshine_hours):
    return POWER_CAPACITY * sunshine_hours * EFFICIENCY
@app.route('/weather_forecast', methods=['GET'])
def weather_forecast():
    latitude = request.args.get('latitude', type=float)
    longitude = request.args.get('longitude', type=float)
    if latitude is None or longitude is None:
        return jsonify({'error': 'Wymagane parametry: latitude, longitude'}), 400
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ["temperature_2m_max", "temperature_2m_min", "sunshine_duration", "precipitation_sum", "weathercode"]
    }
    responses = openmeteo.weather_api(url, params=params)
    if not responses:
        return jsonify({'error': 'Błąd API pogodowego'}), 500
    response = responses[0]
    daily = response.Daily()
    daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy().astype(float)
    daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy().astype(float)
    daily_sunshine_duration = daily.Variables(2).ValuesAsNumpy().astype(float)
    daily_precipitation_sum = daily.Variables(3).ValuesAsNumpy().astype(float)
    daily_weathercode = daily.Variables(4).ValuesAsNumpy().astype(float)

    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        )
    }
    daily_data["temperature_2m_max"] = daily_temperature_2m_max
    daily_data["temperature_2m_min"] = daily_temperature_2m_min
    daily_data["sunshine_duration"] = daily_sunshine_duration
    daily_data["precipitation_sum"] = daily_precipitation_sum
    daily_data["weather_icon"] = daily_weathercode

    forecast = []
    for i in range(len(daily_data["date"])):
        date = daily_data["date"][i]
        max_temp = daily_data["temperature_2m_max"][i]
        min_temp = daily_data["temperature_2m_min"][i]
        sunshine_hours = daily_data["sunshine_duration"][i]/3600
        energy_generated = calculate_solar_energy(sunshine_hours)
        weather_icon = daily_data["weather_icon"][i]

        forecast.append({
            'date': date.strftime('%Y-%m-%d'),
            'max_temp': max_temp,
            'min_temp': min_temp,
            'sunshine_hours': sunshine_hours,
            'energy_generated_kWh': energy_generated,
            'weather_icon': weather_icon
        })

    return jsonify(forecast)

@app.route('/weekly_weather_summary', methods=['GET'])
def weekly_weather_summary():
    latitude = request.args.get('latitude', type=float)
    longitude = request.args.get('longitude', type=float)
    if latitude is None or longitude is None:
        return jsonify({'error': 'Wymagane parametry: latitude, longitude'}), 400
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ["surface_pressure"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "sunshine_duration", "precipitation_sum"]
    }
    responses = openmeteo.weather_api(url, params=params)
    if not responses:
        return jsonify({'error': 'Błąd API pogodowego'}), 500
    response = responses[0]
    hourly = response.Hourly()
    hourly_surface_pressure = hourly.Variables(0).ValuesAsNumpy()
    avg_pressure = hourly_surface_pressure.mean()
    daily = response.Daily()
    daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
    daily_sunshine_duration = daily.Variables(2).ValuesAsNumpy()
    daily_precipitation_sum = daily.Variables(3).ValuesAsNumpy()
    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        ),
        "temperature_2m_max": daily_temperature_2m_max,
        "temperature_2m_min": daily_temperature_2m_min,
        "sunshine_duration": daily_sunshine_duration,
        "precipitation_sum": daily_precipitation_sum
    }
    daily_dataframe = pd.DataFrame(daily_data)
    weekly_dataframe = daily_dataframe[daily_dataframe["date"] < pd.to_datetime("now", utc=True) + pd.Timedelta(days=7)]
    max_temp = weekly_dataframe["temperature_2m_max"].max()
    min_temp = weekly_dataframe["temperature_2m_min"].min()
    avg_sunshine = weekly_dataframe["sunshine_duration"].mean()
    rainy_days_count = len(weekly_dataframe[weekly_dataframe["precipitation_sum"] > 0])
    if rainy_days_count >= 4:
        weather_summary = "Tydzień z opadami"
    else:
        weather_summary = "Tydzień bez opadów"


    summary = {
        "avg_pressure": float(avg_pressure),
        "avg_sunshine": float(avg_sunshine),
        "max_temp": float(max_temp),
        "min_temp": float(min_temp),
        "weather_summary": weather_summary
    }

    return jsonify(summary)

if __name__ == '__main__':
    app.run(debug=True)


import pytest
from main import app
import json


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_weather_forecast(client):
    response = client.get('/weather_forecast?latitude=50.0847592&longitude=19.996796')
    assert response.status_code == 200
    forecast = json.loads(response.data)
    assert len(forecast) == 7
    assert 'date' in forecast[0]
    assert 'max_temp' in forecast[0]
    assert 'energy_generated_kWh' in forecast[0]



def test_weather_forecast_missing_params(client):
    response = client.get('/weather_forecast')
    assert response.status_code == 400
    error_response = json.loads(response.data)
    assert error_response['error'] == 'Wymagane parametry: latitude, longitude'


def test_weekly_weather_summary(client):
    response = client.get('/weekly_weather_summary?latitude=50.0847592&longitude=19.996796')
    assert response.status_code == 200
    summary = json.loads(response.data)
    assert 'avg_pressure' in summary
    assert 'avg_sunshine' in summary
    assert 'max_temp' in summary
    assert 'min_temp' in summary
    assert 'weather_summary' in summary


def test_weekly_weather_summary_missing_params(client):
    response = client.get('/weekly_weather_summary')
    assert response.status_code == 400
    error_response = json.loads(response.data)
    assert error_response['error'] == 'Wymagane parametry: latitude, longitude'

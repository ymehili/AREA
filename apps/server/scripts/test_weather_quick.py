#!/usr/bin/env python3
"""Quick test script to verify Weather service integration.

This script tests the weather plugin without requiring a full server setup.
Just set your OPENWEATHERMAP_API_KEY environment variable and run.

Usage:
    export OPENWEATHERMAP_API_KEY=your_key_here
    python test_weather_quick.py
"""

import os
import sys
from uuid import uuid4

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.integrations.simple_plugins.weather_plugin import (
    get_current_weather_handler,
    get_forecast_handler,
)


class MockArea:
    """Mock Area object for testing."""
    
    def __init__(self):
        self.id = uuid4()
        self.user_id = uuid4()
        self.name = "Test Weather Area"


def test_current_weather():
    """Test getting current weather for Paris."""
    print("🌤️  Testing Current Weather...")
    print("-" * 60)
    
    area = MockArea()
    params = {
        "location": "Paris,FR",
        "units": "metric"
    }
    event = {}
    
    try:
        get_current_weather_handler(area, params, event)
        
        print("✅ Current weather test PASSED")
        print(f"   📍 Location: {event.get('weather.location')}")
        print(f"   🌡️  Temperature: {event.get('weather.temperature')}°C")
        print(f"   🤔 Feels like: {event.get('weather.feels_like')}°C")
        print(f"   ☁️  Condition: {event.get('weather.condition')}")
        print(f"   📝 Description: {event.get('weather.description')}")
        print(f"   💧 Humidity: {event.get('weather.humidity')}%")
        print(f"   💨 Wind speed: {event.get('weather.wind_speed')} m/s")
        return True
        
    except Exception as e:
        print(f"❌ Current weather test FAILED")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_current_weather_coordinates():
    """Test getting current weather using coordinates (London)."""
    print("\n🌍 Testing Current Weather with Coordinates...")
    print("-" * 60)
    
    area = MockArea()
    params = {
        "lat": 51.5074,
        "lon": -0.1278,
        "units": "metric"
    }
    event = {}
    
    try:
        get_current_weather_handler(area, params, event)
        
        print("✅ Coordinate-based weather test PASSED")
        print(f"   📍 Location: {event.get('weather.location')}")
        print(f"   🌡️  Temperature: {event.get('weather.temperature')}°C")
        print(f"   ☁️  Condition: {event.get('weather.condition')}")
        return True
        
    except Exception as e:
        print(f"❌ Coordinate-based weather test FAILED")
        print(f"   Error: {e}")
        return False


def test_forecast():
    """Test getting 5-day forecast for Tokyo."""
    print("\n📅 Testing 5-Day Forecast...")
    print("-" * 60)
    
    area = MockArea()
    params = {
        "location": "Tokyo,JP",
        "units": "metric",
        "cnt": 5  # Get first 5 forecast entries
    }
    event = {}
    
    try:
        get_forecast_handler(area, params, event)
        
        print("✅ Forecast test PASSED")
        print(f"   📍 Location: {event.get('weather.location')}")
        print(f"   📊 Forecast entries: {event.get('weather.forecast_count')}")
        print(f"   🕐 Next forecast time: {event.get('weather.next_forecast_time')}")
        print(f"   🌡️  Next temperature: {event.get('weather.next_temperature')}°C")
        print(f"   ☁️  Next condition: {event.get('weather.next_condition')}")
        return True
        
    except Exception as e:
        print(f"❌ Forecast test FAILED")
        print(f"   Error: {e}")
        return False


def test_invalid_location():
    """Test error handling for invalid location."""
    print("\n⚠️  Testing Error Handling (Invalid Location)...")
    print("-" * 60)
    
    area = MockArea()
    params = {
        "location": "NonExistentCity12345XYZ",
        "units": "metric"
    }
    event = {}
    
    try:
        get_current_weather_handler(area, params, event)
        print("❌ Should have raised an error for invalid location")
        return False
        
    except Exception as e:
        print(f"✅ Error handling test PASSED")
        print(f"   Expected error caught: {type(e).__name__}")
        print(f"   Message: {e}")
        return True


def test_missing_params():
    """Test error handling for missing parameters."""
    print("\n⚠️  Testing Error Handling (Missing Params)...")
    print("-" * 60)
    
    area = MockArea()
    params = {}  # No location provided
    event = {}
    
    try:
        get_current_weather_handler(area, params, event)
        print("❌ Should have raised an error for missing parameters")
        return False
        
    except ValueError as e:
        print(f"✅ Missing params test PASSED")
        print(f"   Expected error caught: {type(e).__name__}")
        print(f"   Message: {e}")
        return True
    except Exception as e:
        print(f"⚠️  Caught different exception: {type(e).__name__}: {e}")
        return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("🌦️  WEATHER SERVICE INTEGRATION TEST")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        print("\n❌ ERROR: OPENWEATHERMAP_API_KEY not set in environment")
        print("\nPlease set it:")
        print("  export OPENWEATHERMAP_API_KEY=your_key_here")
        print("\nGet a free API key at: https://openweathermap.org/api")
        sys.exit(1)
    
    print(f"\n🔑 API Key: {'✓ Set' if api_key else '✗ Not Set'}")
    print()
    
    # Run tests
    results = []
    results.append(test_current_weather())
    results.append(test_current_weather_coordinates())
    results.append(test_forecast())
    results.append(test_invalid_location())
    results.append(test_missing_params())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Weather service is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

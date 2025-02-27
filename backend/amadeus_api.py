import requests
import time

# Your Amadeus API credentials (Replace these with actual values)
API_KEY = "nrIGgNBdV5Zd0hEKOerUaSddSkZjDAto"
API_SECRET = "c4hS8c7d88hppElp"

# Store the token and expiry time
access_token = None
token_expiry = 0  # Stores UNIX timestamp

def get_access_token():
    """Get Amadeus API access token (handles token caching)."""
    global access_token, token_expiry
    
    # Use cached token if still valid
    if access_token and time.time() < token_expiry:
        return access_token

    # Request new token
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": API_SECRET
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()  # Raise error for bad status codes

        json_response = response.json()
        access_token = json_response["access_token"]
        token_expiry = time.time() + json_response["expires_in"]  # Store expiry time

        return access_token
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Amadeus token: {e}")
        return None

def search_flights(origin, destination, departure_date, adults=1):
    """Search for flights using Amadeus API."""
    token = get_access_token()
    if not token:
        return None

    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": adults,
        "currencyCode": "USD",  # Change if needed
        "max": 5  # Get top 5 results
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()  # Return flight data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching flights: {e}")
        return None

def search_hotels(city_code, check_in, check_out, adults=1):
    """Search for hotels using Amadeus API."""
    token = get_access_token()
    if not token:
        return None

    url = "https://test.api.amadeus.com/v2/shopping/hotel-offers"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    params = {
        "cityCode": city_code,
        "checkInDate": check_in,
        "checkOutDate": check_out,
        "adults": adults,
        "currency": "USD",
        "radius": 5,
        "radiusUnit": "KM",
        "paymentPolicy": "NONE",
        "includeClosed": False,
        "bestRateOnly": True,
        "view": "FULL"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()  # Return hotel data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching hotels: {e}")
        return None

def get_place_recommendations(latitude, longitude):
    """Get place recommendations using Amadeus API."""
    token = get_access_token()
    if not token:
        return None

    url = "https://test.api.amadeus.com/v1/reference-data/locations/points-of-interest"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": 10,
        "category": "SIGHTS",  # Options: SIGHTS, NIGHTLIFE, RESTAURANT, SHOPPING
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()  # Return place recommendations

    except requests.exceptions.RequestException as e:
        print(f"Error fetching places: {e}")
        return None

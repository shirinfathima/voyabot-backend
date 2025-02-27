from amadeus_api import search_flights, search_hotels, get_place_recommendations

# 🛫 Test Flight Search
print("Testing Flight Search...")
flights = search_flights("DEL", "DXB", "2025-03-10")
print(f"Flights: {flights}\n")

# 🏨 Test Hotel Search
print("Testing Hotel Search...")
hotels = search_hotels("DXB", "2025-03-10", "2025-03-15")
print(f"Hotels: {hotels}\n")

# 📍 Test Place Recommendations
print("Testing Place Recommendations...")
places = get_place_recommendations(25.276987, 55.296249)  # Dubai latitude/longitude
print(f"Places: {places}\n")


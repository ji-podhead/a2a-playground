# Mock flight database
MOCK_FLIGHTS = {
    "Paris": [
        {"id": "FL100", "airline": "AirFrance", "departure_time": "10:00", "arrival_time": "12:00", "price": 250},
        {"id": "FL101", "airline": "EasyJet", "departure_time": "14:00", "arrival_time": "16:00", "price": 180},
    ],
    "London": [
        {"id": "FL200", "airline": "British Airways", "departure_time": "09:00", "arrival_time": "10:00", "price": 150},
        {"id": "FL201", "airline": "Ryanair", "departure_time": "13:00", "arrival_time": "14:00", "price": 90},
    ]
}

# Mock hotel database
MOCK_HOTELS = {
    "Paris": [
        {"id": "HO100", "name": "Hotel Eiffel", "location": "Near Eiffel Tower", "price_per_night": 150, "amenities": ["WiFi", "Breakfast"]},
        {"id": "HO101", "name": "Louvre Boutique", "location": "Near Louvre Museum", "price_per_night": 120, "amenities": ["WiFi"]},
    ],
    "London": [
        {"id": "HO200", "name": "The Thames View", "location": "Riverside", "price_per_night": 200, "amenities": ["WiFi", "Gym", "Pool"]},
        {"id": "HO201", "name": "Covent Garden Inn", "location": "Theatreland", "price_per_night": 130, "amenities": ["WiFi", "Bar"]},
    ]
}

def search_flights_api(destination, date):
    """Mock API to search for flights."""
    print(f"[Flight API] Searching flights for {destination} on {date}...")
    return MOCK_FLIGHTS.get(destination, [])

def search_hotels_api(destination, check_in_date, check_out_date):
    """Mock API to search for hotels."""
    print(f"[Hotel API] Searching hotels in {destination} from {check_in_date} to {check_out_date}...")
    return MOCK_HOTELS.get(destination, [])

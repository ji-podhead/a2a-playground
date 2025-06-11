# Mock flight database
MOCK_FLIGHTS = {
    "Paris": [
        {"id": "FL100", "airline": "AirFrance", "departure_city": "New York", "arrival_city": "Paris", "departure_time": "10:00", "arrival_time": "22:00", "price": 550, "currency": "USD"},
        {"id": "FL101", "airline": "EasyJet", "departure_city": "London", "arrival_city": "Paris", "departure_time": "14:00", "arrival_time": "16:00", "price": 180, "currency": "EUR"},
    ],
    "London": [
        {"id": "FL200", "airline": "British Airways", "departure_city": "New York", "arrival_city": "London", "departure_time": "09:00", "arrival_time": "21:00", "price": 600, "currency": "USD"},
        {"id": "FL201", "airline": "Ryanair", "departure_city": "Dublin", "arrival_city": "London", "departure_time": "13:00", "arrival_time": "14:00", "price": 90, "currency": "EUR"},
    ],
    "Berlin": [
        {"id": "FL300", "airline": "Lufthansa", "departure_city": "Frankfurt", "arrival_city": "Berlin", "departure_time": "07:00", "arrival_time": "08:00", "price": 120, "currency": "EUR"},
    ]
}

# Mock hotel database
MOCK_HOTELS = {
    "Paris": [
        {"id": "HO100", "name": "Hotel Eiffel", "location": "Near Eiffel Tower", "price_per_night": 150, "currency": "EUR", "amenities": ["WiFi", "Breakfast"], "rating": 4.5},
        {"id": "HO101", "name": "Louvre Boutique", "location": "Near Louvre Museum", "price_per_night": 220, "currency": "EUR", "amenities": ["WiFi", "Gym"], "rating": 4.7},
    ],
    "London": [
        {"id": "HO200", "name": "The Thames View", "location": "Riverside", "price_per_night": 200, "currency": "GBP", "amenities": ["WiFi", "Gym", "Pool"], "rating": 4.8},
        {"id": "HO201", "name": "Covent Garden Inn", "location": "Theatreland", "price_per_night": 130, "currency": "GBP", "amenities": ["WiFi", "Bar"], "rating": 4.2},
    ],
    "Berlin": [
        {"id": "HO300", "name": "Brandenburg Gate Hotel", "location": "Near Brandenburg Gate", "price_per_night": 180, "currency": "EUR", "amenities": ["WiFi", "Sauna", "Restaurant"], "rating": 4.6},
    ]
}

def get_mock_flights(destination: str, date: str):
    """Mock function to get flights. Date is not used in this mock."""
    print(f"[MockData] Searching flights for {destination} on {date}...")
    return MOCK_FLIGHTS.get(destination, [])

def get_mock_hotels(destination: str, check_in_date: str, check_out_date: str):
    """Mock function to get hotels. Dates are not used in this mock."""
    print(f"[MockData] Searching hotels in {destination} from {check_in_date} to {check_out_date}...")
    return MOCK_HOTELS.get(destination, [])

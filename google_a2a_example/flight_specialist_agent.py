from shared_utils import search_flights_api

class FlightSpecialistAgent:
    def __init__(self):
        self.name = "Flight Specialist Agent"

    def search_flights(self, destination, date):
        """Searches for flights using the mock API."""
        print(f"[{self.name}] Received request to find flights to {destination} for {date}.")
        flights = search_flights_api(destination, date)
        if flights:
            print(f"[{self.name}] Found {len(flights)} flights.")
            return flights
        else:
            print(f"[{self.name}] No flights found for {destination}.")
            return []

    def process_request(self, request):
        """Processes a request dictionary."""
        if request.get("task") == "find_flights":
            destination = request.get("destination")
            date = request.get("date")
            if destination and date:
                return self.search_flights(destination, date)
        return {"error": "Invalid request for Flight Specialist"}

from shared_utils import search_hotels_api

class HotelSpecialistAgent:
    def __init__(self):
        self.name = "Hotel Specialist Agent"

    def search_hotels(self, destination, check_in_date, check_out_date):
        """Searches for hotels using the mock API."""
        print(f"[{self.name}] Received request to find hotels in {destination} from {check_in_date} to {check_out_date}.")
        hotels = search_hotels_api(destination, check_in_date, check_out_date)
        if hotels:
            print(f"[{self.name}] Found {len(hotels)} hotels.")
            return hotels
        else:
            print(f"[{self.name}] No hotels found in {destination}.")
            return []

    def process_request(self, request):
        """Processes a request dictionary."""
        if request.get("task") == "find_hotels":
            destination = request.get("destination")
            check_in = request.get("check_in_date")
            check_out = request.get("check_out_date")
            if destination and check_in and check_out:
                return self.search_hotels(destination, check_in, check_out)
        return {"error": "Invalid request for Hotel Specialist"}

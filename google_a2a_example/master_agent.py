from flight_specialist_agent import FlightSpecialistAgent
from hotel_specialist_agent import HotelSpecialistAgent

class MasterAgent:
    def __init__(self):
        self.name = "Master Travel Planner Agent"
        self.flight_agent = FlightSpecialistAgent()
        self.hotel_agent = HotelSpecialistAgent()

    def get_user_preferences(self):
        """Gets travel preferences from the user (mocked for now)."""
        print(f"[{self.name}] Welcome to the Travel Planner!")
        # In a real scenario, this would use request_user_input or similar
        destination = input("Where would you like to go? (e.g., Paris, London): ")
        date = input("When would you like to travel? (e.g., 2024-12-24): ")
        duration = int(input("For how many nights would you like to stay?: ")) # e.g., 3

        # Simple way to calculate check_out_date for this example
        # This doesn't handle month/year rollovers correctly, but is fine for a demo
        from datetime import datetime, timedelta
        check_in_date_obj = datetime.strptime(date, "%Y-%m-%d")
        check_out_date_obj = check_in_date_obj + timedelta(days=duration)
        check_out_date = check_out_date_obj.strftime("%Y-%m-%d")

        print(f"[{self.name}] User preferences: Destination: {destination}, Date: {date}, Duration: {duration} nights (Check-out: {check_out_date})")
        return {"destination": destination, "date": date, "check_in_date": date, "check_out_date": check_out_date}

    def plan_trip(self):
        user_prefs = self.get_user_preferences()

        print(f"\n[{self.name}] Delegating to Flight Specialist...")
        flight_request = {
            "task": "find_flights",
            "destination": user_prefs["destination"],
            "date": user_prefs["date"]
        }
        flight_options = self.flight_agent.process_request(flight_request)

        print(f"\n[{self.name}] Delegating to Hotel Specialist...")
        hotel_request = {
            "task": "find_hotels",
            "destination": user_prefs["destination"],
            "check_in_date": user_prefs["check_in_date"],
            "check_out_date": user_prefs["check_out_date"]
        }
        hotel_options = self.hotel_agent.process_request(hotel_request)

        self.present_plan(user_prefs, flight_options, hotel_options)

    def present_plan(self, prefs, flights, hotels):
        print(f"\n--- [{self.name}] Your Travel Plan ---")
        print(f"Destination: {prefs['destination']}")
        print(f"Travel Date: {prefs['date']}")
        print(f"Check-in: {prefs['check_in_date']}, Check-out: {prefs['check_out_date']}")

        print("\n--- Flight Options ---")
        if flights and not isinstance(flights, dict) and "error" not in flights:
            for flight in flights:
                print(f"- {flight['airline']} ({flight['id']}): {flight['departure_time']} -> {flight['arrival_time']}, Price: ${flight['price']}")
        elif isinstance(flights, dict) and "error" in flights:
            print(f"Error finding flights: {flights['error']}")
        else:
            print("No flights found or error in flight data.")

        print("\n--- Hotel Options ---")
        if hotels and not isinstance(hotels, dict) and "error" not in hotels:
            for hotel in hotels:
                print(f"- {hotel['name']} ({hotel['location']}): Price: ${hotel['price_per_night']}/night, Amenities: {', '.join(hotel['amenities'])}")
        elif isinstance(hotels, dict) and "error" in hotels:
            print(f"Error finding hotels: {hotels['error']}")
        else:
            print("No hotels found or error in hotel data.")
        print("------------------------------------")

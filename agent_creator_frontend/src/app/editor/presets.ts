import { Node, Edge } from 'reactflow';
import { NodeConfigData } from '@/components/DetailPanel'; // Assuming this path is correct

interface TravelPlannerPreset {
  nodes: Node<NodeConfigData>[]; // Use Node<NodeConfigData> directly
  edges: Edge[];
}

export const travelPlannerPreset: TravelPlannerPreset = {
  nodes: [
    // Ensure each node object here is of type Node<NodeConfigData>
    {
      id: 'master-agent',
      type: 'default', // Using 'default' as 'custom' isn't registered yet. Can be 'masterAgentNode' later.
      position: { x: 250, y: 5 },
      data: {
        label: 'Master Travel Planner',
        name: 'Master Travel Planner Agent', // Custom field, add to NodeConfigData if needed generally
        destination: 'Paris',             // Custom field
        date: '2024-12-24',               // Custom field
        duration: 3,                      // Custom field
        // Standard fields from NodeConfigData
        apiEndpoint: '/api/master_travel_planner',
        pydanticModel: '{\n  "title": "MasterTravelRequest",\n  "type": "object",\n  "properties": {\n    "destination": {"type": "string"},\n    "date": {"type": "string", "format": "date"},\n    "duration": {"type": "integer"}\n  },\n  "required": ["destination", "date", "duration"]\n}',
        jsonResponseConfig: '{\n  "flights_info": "object",\n  "hotel_info": "object"\n}',
      },
    },
    {
      id: 'flight-agent',
      type: 'default',
      position: { x: 100, y: 150 },
      data: {
        label: 'Flight Specialist',
        name: 'Flight Specialist Agent',
        task: 'find_flights',
        apiEndpoint: '/api/flight_specialist',
        pydanticModel: '{\n  "title": "FlightTask",\n  "type": "object",\n  "properties": {\n    "destination": {"type": "string"},\n    "date": {"type": "string", "format": "date"}\n  },\n  "required": ["destination", "date"]\n}',
        jsonResponseConfig: '{\n  "flight_options": "array"\n}',
      },
    },
    {
      id: 'hotel-agent',
      type: 'default',
      position: { x: 400, y: 150 },
      data: {
        label: 'Hotel Specialist',
        name: 'Hotel Specialist Agent',
        task: 'find_hotels',
        apiEndpoint: '/api/hotel_specialist',
        pydanticModel: '{\n  "title": "HotelTask",\n  "type": "object",\n  "properties": {\n    "destination": {"type": "string"},\n    "check_in_date": {"type": "string", "format": "date"},\n    "duration": {"type": "integer"}\n  },\n  "required": ["destination", "check_in_date", "duration"]\n}',
        jsonResponseConfig: '{\n  "hotel_options": "array"\n}',
      },
    },
  ],
  edges: [
    {
      id: 'e-master-flight',
      source: 'master-agent',
      target: 'flight-agent',
      animated: true,
    },
    {
      id: 'e-master-hotel',
      source: 'master-agent',
      target: 'hotel-agent',
      animated: true,
    },
  ],
};

// Add more presets here if needed
// export const anotherPreset = { ... };

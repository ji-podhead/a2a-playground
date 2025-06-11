import os
import uuid
import httpx
import json
from typing import Dict, Any, Optional, List
import inspect # For agent card tool schema

from a2a.types import (
    AgentCard,
    Tool,
    ToolInputSchema,
    ToolOutputSchema,
    Property,
)
from google.adk import Agent as ADKAgent
from google.adk.tools import tool
from google.adk.tools.tool_context import ToolContext
from fastapi import FastAPI, HTTPException

AGENT_NAME = "ShoppingAgent"
AGENT_DESCRIPTION = "Manages a virtual shopping experience, including a catalog, cart, and simulated purchases with virtual funds."
AGENT_VERSION = "0.1.0"
AGENT_ID = uuid.uuid4().hex

PG_INTERFACE_AGENT_URL = os.getenv("PG_INTERFACE_AGENT_URL", "http://pg_interface_agent_service:8001")

VIRTUAL_CATALOG = {
    "virtual_book": {"name": "Virtual Self-Help Book", "price": 10.00, "description": "A book to unlock your virtual potential."},
    "virtual_game": {"name": "Virtual Adventure Game", "price": 25.50, "description": "Embark on a thrilling digital quest."},
    "virtual_coffee": {"name": "Virtual Gourmet Coffee Beans", "price": 15.75, "description": "Premium beans for the discerning virtual palate."},
    "virtual_plant": {"name": "Virtual Desk Plant", "price": 5.25, "description": "Adds a touch of green to your virtual workspace."},
}

user_carts: Dict[str, Dict[str, int]] = {}

class ShoppingAgent(ADKAgent):
    def __init__(self):
        super().__init__(name=AGENT_NAME, instruction="You are a helpful and efficient shopping assistant.")
        self.description = AGENT_DESCRIPTION
        self._a2a_client = httpx.AsyncClient(timeout=30.0)

        self.add_tool(self.view_catalog)
        self.add_tool(self.add_to_cart)
        self.add_tool(self.view_cart)
        self.add_tool(self.checkout)
        self.add_tool(self.get_virtual_balance)
        print(f"[{AGENT_NAME}] Initialized. PG Interface URL: {PG_INTERFACE_AGENT_URL}")

    async def _call_pg_interface_tool(self, sql_query: str) -> Dict[str, Any]:
        # Docstring removed
        message_id = uuid.uuid4().hex
        task_id = uuid.uuid4().hex
        payload = {
            "message_id": message_id,
            "role": "agent",
            "parts": [{"tool_code": {"name": "ExecuteSQLQuery", "args": {"sql_query": sql_query}}}],
            "task_id": task_id
        }
        try:
            print(f"[{AGENT_NAME}] Calling PG Interface: {PG_INTERFACE_AGENT_URL}/messages, SQL: '{sql_query}'")
            response = await self._a2a_client.post(f"{PG_INTERFACE_AGENT_URL}/messages", json=payload)
            response.raise_for_status()
            response_data = response.json()
            print(f"[{AGENT_NAME}] Raw response from PG Interface: {response_data}")

            if response_data and response_data.get("parts"):
                for part_data in response_data["parts"]:
                    if "tool_data" in part_data:
                        if isinstance(part_data["tool_data"], dict) and part_data["tool_data"].get("status") == "error":
                            print(f"ERROR reported within tool_data from PG Interface: {part_data['tool_data']}")
                            return part_data["tool_data"]
                        return {"status": "success", "data": part_data["tool_data"]}
                    if "error" in part_data:
                        error_content = part_data["error"]
                        if isinstance(error_content, dict):
                            err_msg = error_content.get("message", "Unknown error from PG Interface")
                        else:
                            err_msg = str(error_content)
                        print(f"ERROR from downstream agent PG Interface: {err_msg}")
                        return {"status": "error", "error": err_msg, "details": error_content}
            return {"status": "error", "error": "Malformed or empty response from PG Interface", "raw_response": response_data}
        except httpx.HTTPStatusError as e:
            err_text = e.response.text
            print(f"ERROR: HTTP error {e.response.status_code} calling PG Interface: {err_text}")
            return {"status": "error", "error": f"HTTP error {e.response.status_code}: {err_text}"}
        except Exception as e:
            print(f"ERROR: Exception calling PG Interface: {str(e)}")
            return {"status": "error", "error": f"Exception: {str(e)}"}

    @tool()
    async def view_catalog(self, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        # Docstring removed
        return {"status": "success", "catalog": VIRTUAL_CATALOG}

    @tool()
    async def add_to_cart(self, user_id: str, item_name: str, quantity: int, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        # Docstring removed
        if not user_id:
            return {"status": "error", "message": "user_id is required to add items to cart."}
        if item_name not in VIRTUAL_CATALOG:
            return {"status": "error", "message": f"Item '{item_name}' not found in catalog."}
        if not isinstance(quantity, int) or quantity <= 0:
            return {"status": "error", "message": "Quantity must be a positive integer."}

        if user_id not in user_carts:
            user_carts[user_id] = {}

        current_cart = user_carts[user_id]
        current_cart[item_name] = current_cart.get(item_name, 0) + quantity
        print(f"[{AGENT_NAME}] Cart for user {user_id} updated: {current_cart}")
        return {"status": "success", "message": f"Added {quantity} of {item_name} to cart for user {user_id}.", "cart_snippet": {item_name: current_cart[item_name]}}

    @tool()
    async def view_cart(self, user_id: str, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        # Docstring removed
        if not user_id:
            return {"status": "error", "message": "user_id is required to view cart."}

        current_user_cart = user_carts.get(user_id, {})
        if not current_user_cart:
            return {"status": "success", "user_id": user_id, "message": "Your cart is empty.", "cart": {}, "total_cost": 0.0}

        total_cost = 0.0
        detailed_cart_view = {}
        for item_name, quantity_val in current_user_cart.items():
            item_info = VIRTUAL_CATALOG[item_name]
            price = item_info["price"]
            detailed_cart_view[item_name] = {
                "quantity": quantity_val,
                "name": item_info["name"],
                "price_per_item": price,
                "subtotal": round(quantity_val * price, 2)
            }
            total_cost += quantity_val * price

        return {"status": "success", "user_id": user_id, "cart": detailed_cart_view, "total_cost": round(total_cost, 2)}

    @tool()
    async def get_virtual_balance(self, user_id: str, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        # Docstring removed
        if not user_id:
            return {"status": "error", "message": "user_id is required to get balance."}

        sql = f"SELECT balance FROM user_virtual_funds WHERE user_id = '{user_id}';"
        response = await self._call_pg_interface_tool(sql)

        if response.get("status") == "success":
            results = response.get("data", {}).get("results")
            if results and isinstance(results, list) and len(results) > 0:
                balance_value = results[0][0]
                return {"status": "success", "user_id": user_id, "balance": float(balance_value)}
            else:
                return {"status": "success", "user_id": user_id, "balance": 0.0, "message": "No balance record found for user. Balance is 0.00."}
        return response

    @tool()
    async def checkout(self, user_id: str, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        # Docstring removed
        if not user_id:
            return {"status": "error", "message": "user_id is required for checkout."}

        current_user_cart = user_carts.get(user_id, {})
        if not current_user_cart:
            return {"status": "error", "user_id": user_id, "message": "Cart is empty. Nothing to checkout."}

        total_cost = 0.0
        items_purchased_summary = {}
        for item_name, quantity_val in current_user_cart.items():
            item_info = VIRTUAL_CATALOG[item_name]
            price = item_info["price"]
            items_purchased_summary[item_name] = {"quantity": quantity_val, "name": item_info["name"], "price_per_item": price, "subtotal": round(quantity_val * price, 2)}
            total_cost += quantity_val * price
        total_cost = round(total_cost, 2)

        balance_response = await self.get_virtual_balance(user_id=user_id)
        if balance_response.get("status") != "success":
            return {"status": "error", "message": f"Could not retrieve balance for user {user_id}: {balance_response.get('error', 'Unknown error')}"}

        current_balance = balance_response.get("balance", 0.0)

        if total_cost > current_balance:
            return {
                "status": "error",
                "message": f"Insufficient funds for user {user_id}.",
                "user_id": user_id,
                "current_balance": current_balance,
                "total_cost": total_cost,
                "cart_items": items_purchased_summary
            }

        new_balance = round(current_balance - total_cost, 2)

        update_sql = f"UPDATE user_virtual_funds SET balance = {new_balance} WHERE user_id = '{user_id}';"
        update_response = await self._call_pg_interface_tool(update_sql)

        if update_response.get("status") != "success":
            return {
                "status": "error",
                "message": f"Failed to update balance for user {user_id} in database: {update_response.get('error', 'DB update failed')}",
                "user_id": user_id,
                "current_balance": current_balance,
                "total_cost": total_cost,
            }

        if isinstance(update_response.get("data"), dict) and update_response["data"].get("rowcount", 0) == 0 :
             return {
                "status": "error",
                "message": f"Failed to update balance for user {user_id}: User not found in funds table for update.",
                "user_id": user_id, "current_balance": current_balance, "total_cost": total_cost,
            }

        user_carts.pop(user_id, None)
        print(f"[{AGENT_NAME}] Cart for user {user_id} cleared after checkout.")

        return {
            "status": "success",
            "message": f"Checkout successful for user {user_id}! Items purchased.",
            "user_id": user_id,
            "new_balance": new_balance,
            "items_purchased": items_purchased_summary,
            "total_cost": total_cost,
        }

    async def close_clients(self):
        # Docstring removed
        if self._a2a_client and not self._a2a_client.is_closed:
            print(f"[{AGENT_NAME}] Closing A2A client.")
            await self._a2a_client.aclose()

shopping_adk_agent = ShoppingAgent()
app = FastAPI(
    title=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version=AGENT_VERSION,
)

@app.on_event("shutdown")
async def on_app_shutdown():
    # Docstring removed
    print(f"[{AGENT_NAME}] Application shutdown event triggered.")
    await shopping_adk_agent.close_clients()

@app.post("/messages", summary="A2A message endpoint for ShoppingAgent tools")
async def handle_a2a_message(message: Dict[str, Any]):
    print(f"[{AGENT_NAME}] Received A2A message: {json.dumps(message, indent=2)}")
    try:
        part = message.get("parts", [])[0]
        tool_name = part.get("tool_code", {}).get("name")
        tool_args = part.get("tool_code", {}).get("args", {})

        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing tool_name in A2A message part")

        tool_method = shopping_adk_agent.get_tool(tool_name)
        if not tool_method:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found in {AGENT_NAME}")

        result = await tool_method(**tool_args, tool_context=None)

        response_message_id = uuid.uuid4().hex
        response_task_id = message.get("task_id", uuid.uuid4().hex)

        response_part = {}
        if result.get("status") != "success":
            response_part["error"] = {
                "message": result.get("message", result.get("error", "Unknown error executing tool")),
                "details": result
            }
        else:
            response_part["tool_data"] = result

        return {
            "message_id": response_message_id,
            "role": "agent",
            "parts": [response_part],
            "task_id": response_task_id,
            "conversation_id": message.get("conversation_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[{AGENT_NAME}] Critical error processing A2A message: {e}")
        error_response_part = {
            "error": {
                "message": f"Internal server error in {AGENT_NAME}: {str(e)}",
                "type": "ServerError"
            }
        }
        response_message_id = uuid.uuid4().hex
        task_id_for_error = uuid.uuid4().hex
        if isinstance(message, dict) and "task_id" in message:
            task_id_for_error = message["task_id"]

        return {
            "message_id": response_message_id, "role": "agent", "parts": [error_response_part],
            "task_id": task_id_for_error,
        }

@app.get("/health", summary="Health check for ShoppingAgent service")
async def health_check():
    return {"status": "ok", "agent_name": AGENT_NAME, "version": AGENT_VERSION, "pg_interface_url_configured": PG_INTERFACE_AGENT_URL}

@app.get("/", response_model=AgentCard, summary="Get ShoppingAgent Agent Card")
async def get_agent_card_info():
    tools_list = []
    for tool_name, tool_method_obj in shopping_adk_agent.tools.items():
        sig = inspect.signature(tool_method_obj)
        props = {}
        req_params = []
        for param_name, param_obj in sig.parameters.items():
            if param_name not in ["self", "tool_context"]:
                param_type_str = "string"
                if param_obj.annotation == int: param_type_str = "integer"
                elif param_obj.annotation == float: param_type_str = "number"
                elif param_obj.annotation == bool: param_type_str = "boolean"

                props[param_name] = Property(type=param_type_str, description=f"Parameter: {param_name}")
                if param_obj.default == inspect.Parameter.empty:
                    req_params.append(param_name)

        tools_list.append(
            Tool(
                id=tool_name,
                name=tool_name,
                description=inspect.getdoc(tool_method_obj) or "No description provided.", # Use inspect.getdoc
                input_schema=ToolInputSchema(type="object", properties=props, required=req_params),
                output_schema=ToolOutputSchema(type="object", properties={"status": Property(type="string"), "message": Property(type="string")}, additional_properties_type=True)
            )
        )
    return AgentCard(
        id=AGENT_ID,
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        version=AGENT_VERSION,
        publisher="FinancialInsightsAssistantExtensionPack",
        tools=tools_list
    )

if __name__ == "__main__":
    import uvicorn
    print(f"Starting {AGENT_NAME} FastAPI service for local testing on port 8006...")
    uvicorn.run(app, host="0.0.0.0", port=8006, log_level="info")

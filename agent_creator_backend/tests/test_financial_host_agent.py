import unittest
from unittest.mock import patch, AsyncMock, MagicMock # AsyncMock for async methods, MagicMock for general mocking

# Import necessary ADK and A2A types for creating realistic test scenarios
from google.adk.tools.tool_context import ToolContext
from a2a.types import Message, Part, ToolData # Make sure these are importable or mock them if not essential for logic test

# Import the class to test
from agent_creator_backend.financial_host_agent import FinancialHostLogicAgent

# If a2a.types or google.adk.tools are not easily available in the test env,
# create minimal mock versions of them for the tests to run.
# For example:
try:
    from a2a.types import Message, Part, ToolData
except ImportError:
    print("Warning: a2a.types not found, using minimal mocks for testing.")
    class MockPart:
        def __init__(self, tool_data=None, error=None):
            self.tool_data = tool_data
            self.error = error
        def model_dump(self, exclude_none=True): # Add model_dump if used by code under test
            return {"tool_data": self.tool_data} if self.tool_data else {"error": self.error}


    class MockMessage:
        def __init__(self, message_id, role, parts, task_id):
            self.message_id = message_id
            self.role = role
            self.parts = parts
            self.task_id = task_id
        def model_dump(self, exclude_none=True): # Add model_dump if used by code under test
             return {
                "message_id": self.message_id, "role": self.role,
                "parts": [p.model_dump() for p in self.parts], "task_id": self.task_id
            }

    Message = MockMessage
    Part = MockPart
    ToolData = dict # Assuming ToolData is dict-like


class TestFinancialHostLogicAgent(unittest.IsolatedAsyncioTestCase):

    def create_mock_tool_context(self) -> ToolContext:
        # ADK ToolContext might have specific requirements.
        # For now, a simple MagicMock should suffice if no methods on it are called by our code.
        # If methods ARE called (e.g., context.get_last_user_utterance()), mock those specifically.
        mock_context = MagicMock(spec=ToolContext)
        return mock_context

    @patch('httpx.AsyncClient') # Mock the HTTP client used by the agent
    async def test_initialization_and_config(self, MockAsyncClient):
        # Test with default config
        agent_default = FinancialHostLogicAgent()
        self.assertEqual(agent_default.analysis_loop_agent_url, "http://mock_analysis_loop_agent:8005")
        self.assertEqual(agent_default.host_agent_model, "gemini-1.5-flash-latest")
        MockAsyncClient.assert_called_once() # Ensure client is created
        await agent_default.close_clients() # Test closing

        MockAsyncClient.reset_mock()

        # Test with custom config
        custom_config = {
            "ANALYSIS_LOOP_AGENT_URL": "http://custom_analysis:9000",
            "PG_INTERFACE_AGENT_URL": "http://custom_pg:9001",
            "FIN_INTERFACE_AGENT_URL": "http://custom_fin:9002",
            "SHOPPING_AGENT_URL": "http://custom_shop:9003",
            "HOST_AGENT_MODEL": "gemini-pro"
        }
        agent_custom = FinancialHostLogicAgent(config=custom_config)
        self.assertEqual(agent_custom.analysis_loop_agent_url, "http://custom_analysis:9000")
        self.assertEqual(agent_custom.pg_interface_agent_url, "http://custom_pg:9001")
        self.assertEqual(agent_custom.fin_interface_agent_url, "http://custom_fin:9002")
        self.assertEqual(agent_custom.shopping_agent_url, "http://custom_shop:9003")
        self.assertEqual(agent_custom.model, "gemini-pro") # Check if ADK model field is updated
        MockAsyncClient.assert_called_once()
        await agent_custom.close_clients()


    @patch('httpx.AsyncClient')
    async def test_call_downstream_a2a_tool_success(self, MockAsyncClient):
        mock_http_client_instance = MockAsyncClient.return_value

        # Mock the response from the downstream A2A agent
        mock_a2a_response = AsyncMock() # httpx.Response
        mock_a2a_response.status_code = 200
        # Construct a realistic A2A JSON response structure
        mock_response_json = {
            "message_id": "resp_msg_id",
            "task_id": "task_id_from_a2a",
            "role": "agent",
            "parts": [
                {"tool_data": {"name": "DownstreamTool", "data": {"key": "value"}}}
            ]
        }
        mock_a2a_response.json = MagicMock(return_value=mock_response_json)
        mock_a2a_response.raise_for_status = MagicMock() # Ensure it doesn't raise for 200

        mock_http_client_instance.post = AsyncMock(return_value=mock_a2a_response)

        agent = FinancialHostLogicAgent()
        tool_result = await agent._call_downstream_a2a_tool(
            agent_base_url="http://fake_service:8000",
            tool_name="TestTool",
            tool_args={"param": "test_param"}
        )

        mock_http_client_instance.post.assert_called_once()
        # Further assertions can be made on the URL and JSON body of the POST request if needed.
        # args, kwargs = mock_http_client_instance.post.call_args
        # self.assertEqual(args[0], "http://fake_service:8000/messages")

        self.assertEqual(tool_result, {"status": "success", "data": {"name": "DownstreamTool", "data": {"key": "value"}}})
        await agent.close_clients()

    @patch('httpx.AsyncClient')
    async def test_call_downstream_a2a_tool_http_error(self, MockAsyncClient):
        mock_http_client_instance = MockAsyncClient.return_value

        mock_a2a_response = AsyncMock()
        mock_a2a_response.status_code = 500
        mock_a2a_response.text = "Internal Server Error"
        mock_a2a_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Error!", request=MagicMock(), response=mock_a2a_response))

        mock_http_client_instance.post = AsyncMock(return_value=mock_a2a_response)

        agent = FinancialHostLogicAgent()
        tool_result = await agent._call_downstream_a2a_tool(
            agent_base_url="http://fake_service:8000",
            tool_name="TestTool",
            tool_args={}
        )

        self.assertEqual(tool_result['status'], "error")
        self.assertIn("HTTP error 500", tool_result['error'])
        await agent.close_clients()

    @patch('httpx.AsyncClient')
    async def test_call_downstream_a2a_tool_a2a_error_response(self, MockAsyncClient):
        mock_http_client_instance = MockAsyncClient.return_value
        mock_a2a_response = AsyncMock()
        mock_a2a_response.status_code = 200 # Successful HTTP call
        mock_response_json = { # But A2A indicates an error in its payload
            "message_id": "resp_msg_id", "task_id": "task_id_from_a2a", "role": "agent",
            "parts": [{"error": {"message": "A2A specific error occurred"}}]
        }
        mock_a2a_response.json = MagicMock(return_value=mock_response_json)
        mock_a2a_response.raise_for_status = MagicMock()
        mock_http_client_instance.post = AsyncMock(return_value=mock_a2a_response)

        agent = FinancialHostLogicAgent()
        tool_result = await agent._call_downstream_a2a_tool("http://fakeservice", "AnyTool", {})
        self.assertEqual(tool_result, {"status": "error", "error": "A2A specific error occurred"})
        await agent.close_clients()


    @patch('agent_creator_backend.financial_host_agent.FinancialHostLogicAgent._call_downstream_a2a_tool', new_callable=AsyncMock)
    async def test_start_stock_analysis_tool(self, mock_call_downstream):
        agent = FinancialHostLogicAgent()
        mock_tool_context = self.create_mock_tool_context()

        expected_response = {"status": "success", "data": "Analysis started"}
        mock_call_downstream.return_value = expected_response

        stock_symbol = "GOOGL"
        result = await agent.start_stock_analysis(stock_symbol, tool_context=mock_tool_context)

        mock_call_downstream.assert_called_once_with(
            agent.analysis_loop_agent_url, # Ensure it uses the configured URL
            "StartAnalysisLoop",
            {"stock_symbol": stock_symbol}
        )
        self.assertEqual(result, expected_response)
        await agent.close_clients() # Don't forget to close if client was initialized

    @patch('agent_creator_backend.financial_host_agent.FinancialHostLogicAgent._call_downstream_a2a_tool', new_callable=AsyncMock)
    async def test_get_latest_prediction_tool_success_with_data(self, mock_call_downstream):
        agent = FinancialHostLogicAgent()
        mock_tool_context = self.create_mock_tool_context()

        # Simulate a successful response from PgInterfaceAgent via _call_downstream_a2a_tool
        db_query_response = {
            "status": "success",
            "data": {
                "results": [
                    {"prediction_timestamp": "2023-01-01T12:00:00Z", "predicted_value": 150.00, "notes": "Strong buy"}
                ]
            }
        }
        mock_call_downstream.return_value = db_query_response

        stock_symbol = "AAPL"
        result = await agent.get_latest_prediction(stock_symbol, tool_context=mock_tool_context)

        expected_sql = f"SELECT prediction_timestamp, prediction_type, predicted_value, notes FROM stock_predictions WHERE symbol = '{stock_symbol.upper()}' ORDER BY prediction_timestamp DESC LIMIT 1"
        mock_call_downstream.assert_called_once_with(
            agent.pg_interface_agent_url,
            "ExecuteSQLQuery",
            {"sql_query": expected_sql}
        )
        self.assertEqual(result, {"status": "success", "prediction": db_query_response["data"]["results"][0]})
        await agent.close_clients()

    @patch('agent_creator_backend.financial_host_agent.FinancialHostLogicAgent._call_downstream_a2a_tool', new_callable=AsyncMock)
    async def test_get_latest_prediction_tool_no_data(self, mock_call_downstream):
        agent = FinancialHostLogicAgent()
        mock_tool_context = self.create_mock_tool_context()
        db_query_response_no_data = {"status": "success", "data": {"results": []}} # Empty results
        mock_call_downstream.return_value = db_query_response_no_data

        stock_symbol = "MSFT"
        result = await agent.get_latest_prediction(stock_symbol, tool_context=mock_tool_context)

        self.assertEqual(result, {"status": "success", "prediction": "No prediction found for this symbol."})
        await agent.close_clients()

    @patch('agent_creator_backend.financial_host_agent.FinancialHostLogicAgent._call_downstream_a2a_tool', new_callable=AsyncMock)
    async def test_get_latest_prediction_tool_error_from_db(self, mock_call_downstream):
        agent = FinancialHostLogicAgent()
        mock_tool_context = self.create_mock_tool_context()
        db_query_error_response = {"status": "error", "error": "DB connection failed"}
        mock_call_downstream.return_value = db_query_error_response

        stock_symbol = "TSLA"
        result = await agent.get_latest_prediction(stock_symbol, tool_context=mock_tool_context)

        self.assertEqual(result, db_query_error_response) # Should propagate the error response
        await agent.close_clients()

    async def test_release_method(self):
        # The release method for FinancialHostLogicAgent is currently simple.
        # We'll just call it to ensure it runs without error.
        # If it involved async operations, more complex mocking (like for _a2a_client.aclose) would be needed.
        agent = FinancialHostLogicAgent()
        try:
            await agent.release() # It's an async method now
        except Exception as e:
            self.fail(f"agent.release() raised an exception: {e}")
        # Ensure client is closed if it was opened
        # This depends on whether __init__ is called for each test method or once per class.
        # With IsolatedAsyncioTestCase, setUp and tearDown (or per-test instantiation) are common.
        # If agent._a2a_client might not be initialized, add a check.
        if hasattr(agent, '_a2a_client') and agent._a2a_client:
             await agent.close_clients()


if __name__ == '__main__':
    unittest.main(verbosity=2)

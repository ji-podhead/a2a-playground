import unittest
import uuid
from fastapi.testclient import TestClient
from typing import Dict, Any

# Assuming your FastAPI app instance is in agent_creator_backend.main
from agent_creator_backend.main import app
from agent_creator_backend.models import AgentType, AgentStatus, ExecutionStatus

# Mock the actual agent instances and pools to prevent real execution/network calls
# and allow for assertions on their usage.
from unittest.mock import patch, MagicMock, ANY

# It's important that these patches are applied *before* the TestClient interacts with the app
# for routes that would trigger agent creation or execution.

# We need to mock the pools directly in agents.py where they are defined and used.
# Patching them at the source.
mock_a2a_pool_acquire = MagicMock()
mock_a2a_pool_release = MagicMock()
mock_adk_pool_acquire = MagicMock()
mock_adk_pool_release = MagicMock()
mock_financial_pool_acquire = MagicMock()
mock_financial_pool_release = MagicMock()

# Mock agent instances that would be returned by pool.acquire()
mock_a2a_agent_instance = MagicMock()
mock_a2a_agent_instance.execute.return_value = {"a2a_mock_result": "success"}

mock_adk_agent_instance = MagicMock()
mock_adk_agent_instance.execute.return_value = {"adk_mock_result": "success"}

# For FinancialHostLogicAgent, its execution is more complex (async, ADK invoke)
# The placeholder in agents.py returns a synchronous dict. We'll match that.
mock_financial_agent_instance = MagicMock()
# The placeholder result:
financial_placeholder_result = {
    "status": "simulated_success",
    "message": "Financial Host Agent processed (simulated): test input", # Input text will vary
    "notes": "This execution is a synchronous placeholder for an async ADK agent."
}
# We'll have execute return a function that can customize the message based on input
def mock_financial_execute(params):
    input_text = params.get("input_text", "default financial input")
    return {
        "status": "simulated_success",
        "message": f"Financial Host Agent processed (simulated): {input_text}",
        "notes": "This execution is a synchronous placeholder for an async ADK agent."
    }
# The ADK agent itself is not directly executed by calling an 'execute' method in agents.py's current placeholder.
# The placeholder logic is directly in agents.py. So, we might not need to mock execute on financial_agent_instance
# if the pool acquire itself is what we care about, and the logic in agents.py is what's tested.
# However, if the acquired instance's methods *were* called, this is how you'd mock them.
# For FinancialHost, the placeholder in agents.py doesn't call instance.execute().
# It directly crafts a response. So, we only need to ensure it's acquired/released.


# Apply patches using a decorator or context manager for tests.
# We will use a class decorator to patch for all methods in this test class.
@patch('agent_creator_backend.agents.a2a_agent_pool')
@patch('agent_creator_backend.agents.adk_agent_pool')
@patch('agent_creator_backend.agents.financial_host_agent_pool')
class TestAgentAPI(unittest.TestCase):

    client = TestClient(app)

    def setUp(self):
        # Reset mocks before each test
        mock_a2a_pool_acquire.reset_mock(return_value=False, side_effect=False)
        mock_a2a_pool_release.reset_mock(return_value=False, side_effect=False)
        mock_adk_pool_acquire.reset_mock(return_value=False, side_effect=False)
        mock_adk_pool_release.reset_mock(return_value=False, side_effect=False)
        mock_financial_pool_acquire.reset_mock(return_value=False, side_effect=False)
        mock_financial_pool_release.reset_mock(return_value=False, side_effect=False)

        mock_a2a_agent_instance.reset_mock(return_value=False, side_effect=False)
        mock_a2a_agent_instance.execute.return_value = {"a2a_mock_result": "success"}
        mock_adk_agent_instance.reset_mock(return_value=False, side_effect=False)
        mock_adk_agent_instance.execute.return_value = {"adk_mock_result": "success"}

        # Clear in-memory DBs before each test for better isolation
        from agent_creator_backend.agents import db_agents, db_executions
        db_agents.clear()
        db_executions.clear()


    # The mock pool objects are passed as arguments by the @patch decorators
    def test_create_and_execute_a2a_agent(self, mock_financial_pool, mock_adk_pool, mock_a2a_pool):
        # Configure the mock pool's methods
        mock_a2a_pool.acquire = mock_a2a_pool_acquire
        mock_a2a_pool.release = mock_a2a_pool_release
        mock_a2a_pool_acquire.return_value = mock_a2a_agent_instance

        agent_name = "TestA2AAgent"
        agent_config = {"url": "http://testa2a.com"}
        response = self.client.post(
            "/api/agents",
            json={"name": agent_name, "agent_type": AgentType.A2A.value, "config": agent_config}
        )
        self.assertEqual(response.status_code, 201)
        agent_data = response.json()
        self.assertEqual(agent_data["name"], agent_name)
        self.assertEqual(agent_data["agent_type"], AgentType.A2A.value)
        self.assertEqual(agent_data["config"], agent_config)
        agent_id = agent_data["agent_id"]

        # Execute
        exec_params = {"query": "hello a2a"}
        response = self.client.post(
            f"/api/agents/{agent_id}/execute",
            json={"parameters": exec_params}
        )
        self.assertEqual(response.status_code, 202) # Accepted
        exec_data = response.json()

        mock_a2a_pool_acquire.assert_called_once_with(config_override=agent_config)
        mock_a2a_agent_instance.execute.assert_called_once_with(exec_params)
        mock_a2a_pool_release.assert_called_once_with(mock_a2a_agent_instance)

        self.assertEqual(exec_data["status"], ExecutionStatus.COMPLETED.value)
        self.assertEqual(exec_data["result"], {"a2a_mock_result": "success"})


    def test_create_and_execute_adk_agent(self, mock_financial_pool, mock_adk_pool, mock_a2a_pool):
        mock_adk_pool.acquire = mock_adk_pool_acquire
        mock_adk_pool.release = mock_adk_pool_release
        mock_adk_pool_acquire.return_value = mock_adk_agent_instance

        agent_name = "TestADKAgent"
        agent_config = {"project": "test-adk-proj"}
        response = self.client.post(
            "/api/agents",
            json={"name": agent_name, "agent_type": AgentType.ADK.value, "config": agent_config}
        )
        self.assertEqual(response.status_code, 201)
        agent_data = response.json()
        agent_id = agent_data["agent_id"]

        exec_params = {"prompt": "hello adk"}
        response = self.client.post(
            f"/api/agents/{agent_id}/execute",
            json={"parameters": exec_params}
        )
        self.assertEqual(response.status_code, 202)
        exec_data = response.json()

        mock_adk_pool_acquire.assert_called_once_with(config_override=agent_config)
        mock_adk_agent_instance.execute.assert_called_once_with(exec_params)
        mock_adk_pool_release.assert_called_once_with(mock_adk_agent_instance)

        self.assertEqual(exec_data["status"], ExecutionStatus.COMPLETED.value)
        self.assertEqual(exec_data["result"], {"adk_mock_result": "success"})


    def test_create_and_execute_financial_host_agent(self, mock_financial_pool, mock_adk_pool, mock_a2a_pool):
        mock_financial_pool.acquire = mock_financial_pool_acquire
        mock_financial_pool.release = mock_financial_pool_release
        # The acquired instance for FinancialHost is used by name, but its methods are not directly called by the placeholder.
        # We need to import the actual class for spec to avoid issues with isinstance checks if any, or for more detailed mocking.
        from agent_creator_backend.financial_host_agent import FinancialHostLogicAgent
        mock_financial_pool_acquire.return_value = MagicMock(spec=FinancialHostLogicAgent)

        agent_name = "TestFinancialHostAgent"
        agent_config = {"HOST_AGENT_MODEL": "gemini-custom"}
        response = self.client.post(
            "/api/agents",
            json={"name": agent_name, "agent_type": AgentType.FINANCIAL_HOST.value, "config": agent_config}
        )
        self.assertEqual(response.status_code, 201)
        agent_data = response.json()
        agent_id = agent_data["agent_id"]

        exec_params = {"input_text": "What is GOOG stock?"}
        response = self.client.post(
            f"/api/agents/{agent_id}/execute",
            json={"parameters": exec_params}
        )
        self.assertEqual(response.status_code, 202)
        exec_data = response.json()

        mock_financial_pool_acquire.assert_called_once_with(config_override=agent_config)
        mock_financial_pool_release.assert_called_once_with(mock_financial_pool_acquire.return_value)

        self.assertEqual(exec_data["status"], ExecutionStatus.COMPLETED.value)
        expected_simulated_msg = f"Financial Host Agent processed (simulated): {exec_params['input_text']}"
        self.assertEqual(exec_data["result"]["message"], expected_simulated_msg)
        self.assertEqual(exec_data["result"]["status"], "simulated_success")


    def test_list_agents(self, mock_financial_pool, mock_adk_pool, mock_a2a_pool):
        # Since db is cleared in setUp, we expect 0 agents initially for this specific test's scope
        initial_response = self.client.get("/api/agents")
        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(len(initial_response.json()), 0)

        self.client.post("/api/agents", json={"name": "Agent1", "agent_type": "a2a", "config": {}})
        self.client.post("/api/agents", json={"name": "Agent2", "agent_type": "adk", "config": {}})

        response = self.client.get("/api/agents")
        self.assertEqual(response.status_code, 200)
        agents_list = response.json()
        self.assertEqual(len(agents_list), 2)

        found_agent1 = any(agent['name'] == "Agent1" for agent in agents_list)
        found_agent2 = any(agent['name'] == "Agent2" for agent in agents_list)
        self.assertTrue(found_agent1)
        self.assertTrue(found_agent2)

    # TODO: Add tests for get_agent, update_agent, delete_agent, list_executions, get_execution_details

    # No tearDownClass needed if setUp clears the DBs for each test.

if __name__ == '__main__':
    unittest.main(verbosity=2)

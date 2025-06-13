import unittest
from agent_creator_backend.a2a_mock import A2AMock
from agent_creator_backend.adk_mock import ADKMock

class TestMockAgents(unittest.TestCase):

    def test_a2a_mock_creation_and_execution(self):
        config = {"url": "http://a2a.example.com", "token": "test_token"}
        a2a_agent = A2AMock(config=config)

        self.assertEqual(a2a_agent.config, config)

        params = {"query": "test_query", "user_id": 123}
        result = a2a_agent.execute(params=params)

        expected_result = {
            "status": "success",
            "message": "A2A mock execution successful",
            "config": config,
            "params": params
        }
        self.assertEqual(result, expected_result)

        # Test release method (simple print, so just ensure it runs)
        try:
            a2a_agent.release()
        except Exception as e:
            self.fail(f"A2AMock release() method failed: {e}")

    def test_adk_mock_creation_and_execution(self):
        config = {"project_id": "test_project", "model_name": "gemini-test"}
        adk_agent = ADKMock(config=config)

        self.assertEqual(adk_agent.config, config)

        params = {"prompt": "test_prompt", "temperature": 0.5}
        result = adk_agent.execute(params=params)

        expected_result = {
            "status": "success",
            "message": "ADK mock execution successful",
            "config": config,
            "params": params
        }
        self.assertEqual(result, expected_result)

        # Test release method (simple print, so just ensure it runs)
        try:
            adk_agent.release()
        except Exception as e:
            self.fail(f"ADKMock release() method failed: {e}")

if __name__ == '__main__':
    unittest.main(verbosity=2)

import unittest
import time # For testing timed aspects if any, or just for printouts
from typing import Dict, Any
from agent_creator_backend.object_pool import ObjectPool

# Mock object for testing the pool
class MockPooledObject:
    instance_counter = 0

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.id = MockPooledObject.instance_counter
        MockPooledObject.instance_counter += 1
        self.is_released = False
        print(f"MockPooledObject {self.id} created with config: {config}")

    def use(self):
        print(f"MockPooledObject {self.id} is being used with config {self.config}.")
        if self.is_released:
            raise Exception(f"Object {self.id} used after being released to pool (but before re-acquire). This indicates a bug in test or object state if not reset by pool's release logic.")
        return f"Object {self.id} used with {self.config.get('param', 'default_param')}"

    def release(self):
        # This method is called by the ObjectPool's release mechanism
        print(f"MockPooledObject {self.id} (config: {self.config}) being reset/marked as released for pooling.")
        self.is_released = True # Simulate a state reset

    def __del__(self):
        print(f"MockPooledObject {self.id} (config: {self.config}) is being deleted.")


def create_mock_pooled_object(config: Dict[str, Any]) -> MockPooledObject:
    return MockPooledObject(config=config)

class TestObjectPool(unittest.TestCase):

    def setUp(self):
        MockPooledObject.instance_counter = 0 # Reset counter for each test

    def test_pool_creation_initial_size(self):
        pool = ObjectPool(creator=create_mock_pooled_object, initial_size=3, config={"type": "test"})
        self.assertEqual(pool.get_pool_size(), 3)
        # Check that 3 objects were created with the pool's default config
        obj = pool.acquire() # Should take from pool
        self.assertEqual(obj.config, {"type": "test"})
        self.assertEqual(MockPooledObject.instance_counter, 3) # No new objects created on acquire
        pool.release(obj)

    def test_acquire_release(self):
        pool = ObjectPool(creator=create_mock_pooled_object, initial_size=1, config={"param": "initial"})
        self.assertEqual(MockPooledObject.instance_counter, 1)

        obj1 = pool.acquire()
        self.assertIsNotNone(obj1)
        self.assertEqual(obj1.id, 0) # Assuming first object created
        self.assertEqual(obj1.config, {"param": "initial"})
        obj1.is_released = False # Mark as not released for use
        obj1.use()

        self.assertEqual(pool.get_pool_size(), 0) # Pool should be empty

        pool.release(obj1)
        self.assertTrue(obj1.is_released) # Check if release method was called on object
        self.assertEqual(pool.get_pool_size(), 1) # Object returned to pool

        obj2 = pool.acquire() # Should reuse obj1
        self.assertIs(obj1, obj2) # Should be the same instance
        obj2.is_released = False # Mark as not released for use
        obj2.use()
        self.assertEqual(pool.get_pool_size(), 0)
        pool.release(obj2)

    def test_acquire_new_when_pool_empty(self):
        pool = ObjectPool(creator=create_mock_pooled_object, initial_size=0, config={"param": "default"})
        self.assertEqual(MockPooledObject.instance_counter, 0)
        self.assertEqual(pool.get_pool_size(), 0)

        obj1_config = {"param": "custom1"}
        obj1 = pool.acquire(config_override=obj1_config) # Pool is empty, creates new
        self.assertIsNotNone(obj1)
        self.assertEqual(MockPooledObject.instance_counter, 1) # One object created
        self.assertEqual(obj1.config, obj1_config) # Uses override config
        obj1.is_released = False
        obj1.use()

        self.assertEqual(pool.get_pool_size(), 0) # Pool still empty as obj1 is in use
        pool.release(obj1)
        self.assertEqual(pool.get_pool_size(), 1)

    def test_config_override_for_new_objects(self):
        pool = ObjectPool(creator=create_mock_pooled_object, initial_size=0, config={"default_key": "default_value"})

        # Acquire with override, should create a new object with this specific config
        custom_config = {"param": "special", "id_val": 1}
        obj_custom = pool.acquire(config_override=custom_config)
        self.assertEqual(obj_custom.config, custom_config)
        self.assertEqual(MockPooledObject.instance_counter, 1)
        pool.release(obj_custom)

        # Acquire another with different override
        another_custom_config = {"param": "super_special", "id_val": 2}
        obj_another_custom = pool.acquire(config_override=another_custom_config)
        # This should also be a new object if the pool reuses strictly based on config,
        # or if it just gives any available object. Our current pool is simple:
        # it gives an available object if any, or creates new with the override.
        # It does not re-configure existing objects in the pool upon acquisition with override.
        self.assertEqual(obj_another_custom.config, another_custom_config)
        # If obj_custom was released, and acquire doesn't re-configure, then obj_another_custom
        # would be different from obj_custom.
        self.assertNotEqual(id(obj_custom), id(obj_another_custom), "Pool should create a new instance for a different config override if no suitable one exists or if existing ones don't match and are not reconfigured.")
        self.assertEqual(MockPooledObject.instance_counter, 2) # Total 2 objects created
        pool.release(obj_another_custom)

    def test_acquire_uses_pooled_object_ignores_override_if_object_exists(self):
        # This test clarifies the behavior: if an object is in the pool, acquire() returns it.
        # The config_override is primarily for creating *new* objects if the pool is empty.
        # The current ObjectPool does NOT re-configure pooled objects with config_override.
        pool = ObjectPool(creator=create_mock_pooled_object, initial_size=1, config={"original_config": True})
        original_obj = pool.acquire() # Takes the one from initial_size
        self.assertEqual(original_obj.config, {"original_config": True})
        pool.release(original_obj) # Put it back

        # Now acquire with an override. Since an object is available, it should return that one.
        override_config = {"new_config": True}
        reacquired_obj = pool.acquire(config_override=override_config)

        self.assertIs(reacquired_obj, original_obj, "Should reuse the existing object from the pool.")
        self.assertEqual(reacquired_obj.config, {"original_config": True},
                         "The config of the reused object should be its original config, not the override.")
        pool.release(reacquired_obj)

if __name__ == '__main__':
    # Create a directory for tests if it doesn't exist, to avoid FileNotFoundError for test reports
    import os
    if not os.path.exists('agent_creator_backend/tests'):
        os.makedirs('agent_creator_backend/tests')
    unittest.main(verbosity=2)

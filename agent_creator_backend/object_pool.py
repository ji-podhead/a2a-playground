import queue
from typing import Callable, Dict, Any, TypeVar, Generic

T = TypeVar('T')

class ObjectPool(Generic[T]):
    def __init__(self, creator: Callable[[Dict[str, Any]], T], initial_size: int = 0, config: Dict[str, Any] = None):
        self._pool = queue.Queue()
        self._creator = creator
        self._config = config if config is not None else {}
        self._instance_configs: Dict[int, Dict[str, Any]] = {} # To store config per instance if needed

        for i in range(initial_size):
            instance_config = self._config.copy() # Start with base config
            # Potentially customize instance_config further if needed based on 'i' or other logic
            # For now, all initial instances share the same creation config derived from the pool's base config.
            self._instance_configs[id(self._create_new_instance(instance_config))] = instance_config

    def _create_new_instance(self, config_override: Dict[str, Any] = None) -> T:
        # Use config_override if provided, else use the pool's default config
        current_config = config_override if config_override is not None else self._config
        instance = self._creator(current_config)
        self._instance_configs[id(instance)] = current_config # Store config used for this instance
        return instance

    def acquire(self, config_override: Dict[str, Any] = None) -> T:
        try:
            # Try to get an object from the pool without blocking
            instance = self._pool.get_nowait()
            # If a config_override is provided, we might need to re-initialize or check compatibility.
            # For simplicity, this example assumes acquired objects are ready or reconfigured by the caller/wrapper.
            # Or, if instances are meant to be identical, config_override might apply only to new instances.
            print(f"Acquired existing instance {type(instance).__name__} from pool.")
            return instance
        except queue.Empty:
            # Pool is empty, create a new instance
            # If config_override is provided for an acquisition, use it for the new instance.
            print(f"Pool empty, creating new instance with override: {config_override is not None}")
            new_instance = self._create_new_instance(config_override=config_override if config_override else self._config)
            return new_instance

    def release(self, instance: T):
        # Call a 'reset' or 'cleanup' method on the instance if it exists
        if hasattr(instance, 'release'): # Assuming a convention like the mock objects
            try:
                instance.release()
            except Exception as e:
                print(f"Error calling release() on {type(instance).__name__}: {e}")
                # Decide if the instance is still safe to pool, or should be discarded.
                # For now, we'll still pool it.

        self._pool.put(instance)
        instance_config = self._instance_configs.get(id(instance), "Unknown (or default)")
        print(f"Released instance {type(instance).__name__} (config: {instance_config}) back to pool. Pool size: {self._pool.qsize()}")

    def get_pool_size(self) -> int:
        return self._pool.qsize()

    def get_total_objects(self) -> int:
        # This is a simplification; in reality, you'd need to track created vs. pooled.
        # For now, assuming all created objects are either in pool or "in use".
        # This count isn't strictly "total objects managed" unless we add more tracking.
        return self._pool.qsize() # Placeholder - more complex tracking needed for "total ever created" or "currently active + pooled"

# Example usage (optional, for testing within the file)
if __name__ == '__main__':
    class MyMockObject:
        def __init__(self, config):
            self.config = config
            print(f"MyMockObject created with config: {config}")

        def do_work(self, data):
            print(f"MyMockObject doing work with {data} using config {self.config}")
            return f"Work done with {data}"

        def release(self):
            print(f"MyMockObject instance (config: {self.config}) being reset/released.")

    # Creator function for MyMockObject
    def create_my_mock_object(config: Dict[str, Any]) -> MyMockObject:
        return MyMockObject(config)

    # Initialize the pool
    pool = ObjectPool(creator=create_my_mock_object, initial_size=2, config={"default_param": "initial_value"})
    print(f"Initial pool size: {pool.get_pool_size()}")

    # Acquire objects
    obj1_config = {"id": 1, "specific_param": "alpha"}
    obj1 = pool.acquire(config_override=obj1_config)
    obj1.do_work("data1")

    obj2 = pool.acquire() # Uses default config or an available instance
    obj2.do_work("data2")

    obj3_config = {"id": 3, "specific_param": "gamma"}
    obj3 = pool.acquire(config_override=obj3_config) # Likely creates a new one if pool was empty or obj1/obj2 configs differ
    obj3.do_work("data3")


    # Release objects
    pool.release(obj1)
    pool.release(obj2)
    pool.release(obj3)
    print(f"Pool size after releases: {pool.get_pool_size()}")

    # Acquire again, should reuse
    obj4 = pool.acquire() # Config of reused object depends on what was released and pool's behavior
    obj4.do_work("data4")
    pool.release(obj4)
    print(f"Final pool size: {pool.get_pool_size()}")

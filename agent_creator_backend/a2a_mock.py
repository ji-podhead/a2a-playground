class A2AMock:
    def __init__(self, config: dict):
        self.config = config
        print(f"A2AMock initialized with config: {config}")

    def execute(self, params: dict) -> dict:
        print(f"A2AMock executing with params: {params}")
        return {"status": "success", "message": "A2A mock execution successful", "config": self.config, "params": params}

    def release(self):
        print("A2AMock instance released")

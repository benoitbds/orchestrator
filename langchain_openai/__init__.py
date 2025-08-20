class ChatOpenAI:
    def __init__(self, model: str, temperature: float = 0.0):
        self.model = model
        self.temperature = temperature
    def invoke(self, prompt: str):
        class Resp:
            def __init__(self):
                self.content = "stub"
        return Resp()

class ChatOpenAI:
    def __init__(self, model: str, temperature: float = 0.0):
        self.model = model
        self.temperature = temperature
        self._tools = None

    def bind_tools(self, tools):
        self._tools = tools
        return self

    def invoke(self, messages):
        _ = self._tools  # reference stored tools for type checkers
        class Resp:
            def __init__(self):
                self.content = "placeholder"
                self.additional_kwargs = {}
        return Resp()

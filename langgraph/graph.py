END = "END"

class StateGraph:
    def __init__(self, state_cls):
        pass
    def add_node(self, name, fn):
        pass
    def add_edge(self, src, dest):
        pass
    def set_entry_point(self, name):
        pass
    def compile(self):
        class G:
            def invoke(self, state):
                return {}
            async def astream(self, state):
                if False:
                    yield {}
        return G()

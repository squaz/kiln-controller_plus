class BaseObserver:
    def __init__(self, observer_type="generic"):
        self.observer_type = observer_type

    def send(self, data):
        raise NotImplementedError("Observer must implement .send(data)")

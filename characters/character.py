# Headless Character state module
ANIMATIONS = ["idle", "run", "rush", "damage", "die"]
ST_IDLE, ST_RUN, ST_RUSH, ST_DAMAGE, ST_DIE = range(5)

class Character:
    def __init__(self, name: str):
        self.name = name
        self.action = ST_IDLE
        self.alive = True
        
    def set_action(self, action=ST_IDLE):
        if self.alive:
            self.action = action

    def display(self):
        pass

class WhiteCar(Character):
    def __init__(self, *args, **kwargs):
        super().__init__(name="white-cat")
        
    def meow(self):
        pass
        
    def purr(self):
        pass
        
    def stop_purr(self):
        pass

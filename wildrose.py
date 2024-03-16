import pygame


class WGColor:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)


class WhiteCar():
    WIDTH = 32
    HEIGHT = 32
    SCALE = 5
    COLORKEY = (0, 0, 0)

    ST_IDLE = 0
    ST_RUN = 1
    ST_RUSH = 2
    ST_DAMAGE = 3
    ST_DIE = 4

    def __init__(self, fill_width=False):
        self.frame = 0
        self.current_time = pygame.time.get_ticks()
        self.updated_time = pygame.time.get_ticks()
        self.cooldown = 120
        self.action = self.ST_IDLE
        self.animation = []
        for action in ["idle", "run", "rush", "damage", "die",]:
            # load image for the action
            image = self.__load_sprite(f"static/white-cat-{action}.png")
            # calculate how many frames it has
            frames = int(image.get_height() / self.HEIGHT)
            # actions actually store surfaces for each sprite
            action_frames = []
            for frame in range(frames):
                surface = pygame.Surface((self.WIDTH, self.HEIGHT)).convert_alpha()
                surface.blit(image, (0, 0), (0, (frame * self.HEIGHT), self.WIDTH, self.HEIGHT))
                if fill_width:
                    surface = pygame.transform.scale(surface, (400, 400))
                else:
                    surface = pygame.transform.scale(surface, (self.WIDTH * self.SCALE, self.HEIGHT * self.SCALE))
                surface.set_colorkey(self.COLORKEY)
                action_frames.append(surface)
            self.animation.append(action_frames)
        pass

    def __load_sprite(self, image):
        return pygame.image.load(image).convert_alpha()

    def set_action(self, action=ST_IDLE):
        self.action = action

    def toggle_rush(self, ):
        if self.action == self.ST_RUSH:
            self.action = self.ST_IDLE
        else:
            self.action = self.ST_RUSH

    def display(self, root_surface, action=ST_IDLE):
        if root_surface is None:
            return action
        # here we should add position variables for the class
        self.current_time = pygame.time.get_ticks()
        if self.current_time - self.updated_time >= self.cooldown:
            self.frame = (self.frame + 1) % len(self.animation[self.action])
            self.updated_time = self.current_time
        self.frame = 0 if self.frame >= len(self.animation[self.action]) else self.frame
        root_surface.blit(self.animation[self.action][self.frame], (0, 0))


class WildroseGame:
    WIDTH = 400
    HEIGHT = 400

    def __init__(self):
        pygame.init()
        self.window = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Wildrose")
        self.clock = pygame.time.Clock()
        self.running = False
        self.white_car = WhiteCar(fill_width=True)

    def __set_running(self, running=False):
        self.running = running

    def quit(self, ):
        pygame.quit()

    def __fill_background(self, color):
        self.window.fill(color)

    def start(self):
        self.__set_running(True)
        while self.running:
            # handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.__set_running(False)
            # event types also handle white car's action
            # self.white_car.set_action(action=ST_IDLE)

            # update animation
            self.__fill_background(WGColor.BLACK)
            self.white_car.display(self.window, )
            pygame.display.update()
            self.clock.tick(60)
        self.quit()


wg = WildroseGame()
wg.start()


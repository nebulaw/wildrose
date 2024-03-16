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
    ST_DAMAGE = 1

    def __init__(self, full_width=False):
        self.frame = 0
        self.current_time = pygame.time.get_ticks()
        self.updated_time = pygame.time.get_ticks()
        self.cooldown = 120
        self.sprite = self.__load_sprite("static/white-cat-idle.png")
        self.sprite_surfaces = []
        for frame in range(6):
            surface = pygame.Surface((self.WIDTH, self.HEIGHT)).convert_alpha()
            surface.blit(self.sprite, (0, 0), (0, (frame * self.HEIGHT), self.WIDTH, self.HEIGHT))
            if full_width:
                surface = pygame.transform.scale(surface, (400, 400))
            else:
                surface = pygame.transform.scale(surface, (self.WIDTH * self.SCALE, self.HEIGHT * self.SCALE))
            surface.set_colorkey(self.COLORKEY)
            self.sprite_surfaces.append(surface)

    def __load_sprite(self, image):
        return pygame.image.load(image).convert_alpha()

    def display(self, root_surface, action=ST_IDLE):
        if root_surface is None:
            return
        # here we should add position variables for the class
        self.current_time = pygame.time.get_ticks()
        if self.current_time - self.updated_time >= self.cooldown:
            self.frame = (self.frame + 1) % 6
            self.updated_time = self.current_time
        root_surface.blit(self.sprite_surfaces[self.frame], (0, 0))


class WildroseGame:
    WIDTH = 400
    HEIGHT = 400

    def __init__(self):
        pygame.init()
        self.window = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Wildrose")
        self.clock = pygame.time.Clock()
        self.running = False
        self.white_car = WhiteCar(full_width=True)
        self.clock_last_update = pygame.time.get_ticks()
        self.animation_cooldown = 200

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

            # update animation
            self.__fill_background(WGColor.BLACK)
            self.white_car.display(self.window)
            pygame.display.update()
            self.clock.tick(60)
        self.quit()


wg = WildroseGame()
wg.start()


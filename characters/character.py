# Name: Wildrose
# Created By: Karlo Tsutskiridze
# Date: 03-17-2024

import pygame as pg


"""
animations are predefined atm
"""
ANIMATIONS = ["idle", "run", "rush", "damage", "die"]
ST_IDLE, ST_RUN, ST_RUSH, ST_DAMAGE, ST_DIE = range(5)

# TODO: create queue for actions
#       support for intelligent queueing these actions
#       and clearing it if necessary
class Character:
    """Character class

    This class should be inherited if you're developing new character.
    The only thing you need to provide is sprites for already defined
    actions

    """
    def __init__(self, name, root_surface=None, sprite_colorkey=(0, 0, 0), sprite_scale=1.0, sprite_w=32, sprite_h=32, sprite_orientation=1, fill_width=False, frame_cooldown=120):
        """Initialize method for a character

        This method is generalized and necessary to be called in each
        child class. This is designed this way to make character-development
        process easier.

        Parameters
        ----------
        name : str
            The name of the character which will be used to load sprites
            from static/{name}-{action}.png directory
        root_surface: Surface, optional
            Surface to be the character displayed on
        sprite_colorkey: tuple, optional
            The colorkey that will be used for sprites
        sprite_scale: float, optional
            The value sprites will be scaled by (Default is 1.0)
        sprite_w: int, optional
            The width value for sprites (Default is 32)
        sprite_h: int, optional
            The height value for sprites (Default is 32)
        sprite_orientation: int, optional
            This specifies whether a spritesheet would be vertically
            or horizontally iterated. 1 is for horizontal and 0 is for vertical (Default is 1)
        fill_width: bool, optional
            Use the root surface's width. Simply fills the root surface (Default is False)
        frame_cooldown: int, optional
            The time in milliseconds between each frame (Default is 120)
        """
        self.name = name
        self.root_surface = root_surface
        self.sprite_w = sprite_w
        self.sprite_h = sprite_h
        self.sprite_scale = sprite_scale
        self.sprite_colorkey = sprite_colorkey
        self.sprite_orientation = sprite_orientation
        self.frame = 0
        self.frame_cooldown = frame_cooldown
        self.current_time = pg.time.get_ticks()
        self.updated_time = pg.time.get_ticks()
        self.action = ST_IDLE
        self.alive = True
        self.animation = []
        for action in ANIMATIONS:
            # load sprite
            sprite = self.__load_sprite(f"static/{name}-{action}.png")
            # calculate how many frames it has
            total_frames = sprite.get_height() // sprite_h if sprite_orientation == 1 else sprite.get_width() // sprite_w
            # we create individual surfaces for each frame
            action_frames = []
            for frame in range(total_frames):
                surface = pg.Surface((sprite_w, sprite_h)).convert_alpha()
                # this makes sure that frame is clipped correctly
                area_w = 0 if sprite_orientation == 1 else (sprite_w * frame)
                area_h = 0 if sprite_orientation == 0 else (sprite_h * frame)
                surface.blit(sprite, (0, 0), (area_w, area_h, sprite_w, sprite_h))
                if fill_width:
                    surface = pg.transform.scale(surface, (400, 400))
                else:
                    surface = pg.transform.scale(surface, (sprite_w * sprite_scale, sprite_h * sprite_scale))
                surface.set_colorkey(sprite_colorkey)
                action_frames.append(surface)
            self.animation.append(action_frames)
        # TODO: this is a queue for actions?
        # self.actions = []
        pass

    def __load_sprite(self, image):
        return pg.image.load(image).convert_alpha()

    def set_action(self, action=ST_IDLE):
        """Set character's action
        Parameters
        ----------
        action: int, optional
            Action represented by an integer
        """
        if self.alive:
            self.action = action
        if action == ST_DIE:
            self.frame = 0
        self.sound()

    def register_root_surface(self, root_surface):
        """Modify the surface of the character to be displayed on

        This function is should called when root surface wasn't
        specified while creating a character object

        Parameters
        ----------
        root_surface: Surface
            The surface the character to be shown on
        """
        if root_surface is not None:
            self.root_surface = root_surface

    def handle_event(self, event):
        raise NotImplementedError("Handle event method is not implemented")

    def sound(self):
        raise NotImplementedError("Sound method is not implemented")

    def display(self, ):
        """Display the character

        Raises
        -----
        ValueError:
            This exception raises when root surface was not
            provided for the character
        """
        if self.root_surface is None:
            raise ValueError(f"Root surface for {self.name} was not specified.")
        if self.alive:
            # if its time to update the frame
            # cooldown is the time between rendering each frame
            self.current_time = pg.time.get_ticks()
            if self.current_time - self.updated_time >= self.frame_cooldown:
                self.frame = (self.frame + 1) % len(self.animation[self.action])
                self.updated_time = self.current_time
            # check if it exceeds actions' frames
            if self.frame >= len(self.animation[self.action]):
                self.frame = 0
            # kill the car if its death animation's last frame
            if self.action == ST_DIE and self.frame == len(self.animation[self.action]) - 1:
                self.alive = False
            self.root_surface.blit(self.animation[self.action][self.frame], (0, 0))
        else:
            self.root_surface.blit(self.animation[ST_DIE][-1], (0, 0))


class WhiteCar(Character):
    """Sample character class"""
    def __init__(self, sprite_orientation=1, sprite_scale=1.0, fill_width=True, *args, **kwargs):
        super().__init__(name="white-cat", *args, sprite_orientation=sprite_orientation, sprite_scale=sprite_scale, fill_width=fill_width, **kwargs)
        self.sound_channel = pg.mixer.Channel(4)
        self.sound_purring = pg.mixer.Sound("static/purring-1.ogg")
        self.sound_meow = pg.mixer.Sound("static/meow.wav")
        self.purring = False
        self.meowing = False
        self.mouse_down = False
        self.patting = False

    def meow(self):
        if self.meowing:
            return
        if self.purring:
            self.sound_channel.stop()
            self.purring = False
        if not self.sound_channel.get_busy():
            self.sound_channel.play(self.sound_meow)
            self.meowing = True

    def stop_meow(self):
        if self.meowing and self.sound_channel.get_busy():
            self.sound_channel.stop()
            self.meowing = False

    def purr(self):
        if self.purring:
            return
        if self.meowing:
            self.sound_channel.stop()
            self.meowing = False
        if not self.sound_channel.get_busy():
            self.sound_channel.play(self.sound_purring)
            self.purring = True

    def stop_purr(self):
        if self.purring and self.sound_channel.get_busy():
            self.sound_channel.stop()
            self.purring = False

    def set_action(self, action=ST_IDLE):
        """Set character's action
        Parameters
        ----------
        action: int, optional
            Action represented by an integer
        """
        if self.alive:
            self.action = action
        if action == ST_DIE:
            self.frame = 0
            self.meow()
        if action == ST_DAMAGE:
            self.purr()

    def handle_event(self, event):
        # sound clean up
        if not self.sound_channel.get_busy():
            self.meowing = False
            self.purring = False

        if event.type == pg.MOUSEBUTTONDOWN:
            self.mouse_down = True
            self.purr()
        elif event.type == pg.MOUSEBUTTONUP:
            self.mouse_down = False
            self.stop_purr()
            self.set_action(ST_IDLE)
        elif event.type == pg.MOUSEMOTION:
            if self.mouse_down:
                self.purr()
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_k:
                self.set_action(ST_DIE)
            elif event.key == pg.K_RIGHT:
                self.set_action(ST_RUSH)
        elif event.type == pg.KEYUP:
            if event.key == pg.K_RIGHT:
                self.set_action(ST_IDLE)
        pass


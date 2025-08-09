from typing import List
import pygame as pg

from .sprite import CharacterSprite
from brain import Brain
from brain.tool import Tool

# animations are predefined atm
ANIMATIONS = ["idle", "run", "rush", "damage", "die"]
ST_IDLE, ST_RUN, ST_RUSH, ST_DAMAGE, ST_DIE = range(5)

class Character:
    """Character owns behavior and sound; sprite is delegated to CharacterSprite."""
    def __init__(self, name:str, config:str = "", sprite:CharacterSprite=None, root_surface=None):
        self.name, self.sprite = name, sprite
        self.root_surface = root_surface
        self.action, self.alive = ST_IDLE, True
        self.tools = self._init_tools()
        self.brain = Brain(self, config=config, tools=self.tools)
    def _init_tools(self) -> List[Tool]: return []
    def set_action(self, action=ST_IDLE):
        if self.alive:
            self.action = action
            self.sprite.set_action(action)
            if action == ST_DIE: self.sprite.reset_frame()
        self.sound()
    def register_root_surface(self, root_surface):
        if root_surface is not None: self.root_surface = root_surface
    def handle_event(self, event): raise NotImplementedError("Handle event method is not implemented")
    def sound(self): raise NotImplementedError("Sound method is not implemented")
    def display(self):
        if self.root_surface is None: raise ValueError(f"Root surface for {self.name} was not specified.")
        if self.alive:
            self.sprite.update()
            if self.action == ST_DIE and self.sprite.is_last_frame(): self.alive = False
            self.sprite.draw_centered(self.root_surface)
        else: self.sprite.draw_last_centered(self.root_surface, ST_DIE)

class WhiteCar(Character):
    """Sample character class"""
    def __init__(self, *args, **kwargs):
        spr = CharacterSprite(
            name="white-cat",
            actions=ANIMATIONS,
            sprite_w=32,
            sprite_h=32,
            sprite_scale=16.0,
            sprite_colorkey=(0, 0, 0),
            sprite_orientation=1,
            fill_width=True,
            frame_cooldown=120,
        )
        super().__init__(name="white-cat", sprite=spr, *args, **kwargs)
        self.sound_channel = pg.mixer.Channel(2)
        self.sound_purring = pg.mixer.Sound("static/purring-1.ogg")
        self.sound_meow = pg.mixer.Sound("static/meow.wav")
        self.purring = False
        self.meowing = False
        self.mouse_down = False
        self.patting = False
    def meow(self):
        if self.sound_channel.get_busy(): self.sound_channel.stop()
        self.sound_channel.play(self.sound_meow)
        self.purring = False
    def purr(self):
        if self.purring: return
        if self.sound_channel.get_busy(): self.sound_channel.stop()
        self.sound_channel.play(self.sound_purring, loops=-1)
        self.purring = True
    def stop_purr(self):
        if self.purring and self.sound_channel.get_busy(): self.sound_channel.stop(); self.purring = False
    def set_action(self, action=ST_IDLE):
        if self.alive:
            self.action = action
            self.sprite.set_action(action)
            if action == ST_DIE: self.sprite.reset_frame()
    def handle_event(self, event):
        if not self.alive: return
        if event.type == pg.MOUSEBUTTONDOWN: self.mouse_down = True
        elif event.type == pg.MOUSEBUTTONUP: self.mouse_down = False; self.stop_purr(); self.set_action(ST_IDLE)
        elif event.type == pg.MOUSEMOTION:
            if self.mouse_down: self.purr()
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_k: self.meow(); self.set_action(ST_DIE)
            elif event.key == pg.K_m: self.meow()
            elif event.key == pg.K_RIGHT: self.set_action(ST_RUSH)
        elif event.type == pg.KEYUP:
            if event.key == pg.K_RIGHT: self.set_action(ST_IDLE)

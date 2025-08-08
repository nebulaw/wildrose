import pygame as pg

class CharacterSprite:
    """Sprite system: loads actions, advances frames, renders surfaces."""
    def __init__(self, name: str, actions: list[str], *, sprite_w=32, sprite_h=32, sprite_scale=1.0,
                 sprite_colorkey=(0, 0, 0), sprite_orientation=1, fill_width=False, frame_cooldown=120):
        self.name, self.actions = name, actions
        self.w, self.h, self.scale = sprite_w, sprite_h, sprite_scale
        self.colorkey, self.orient, self.fill_width = sprite_colorkey, sprite_orientation, fill_width
        self.cooldown = frame_cooldown
        self._frames: list[list[pg.Surface]] = []
        self._action = 0
        self._frame = 0
        t = pg.time.get_ticks()
        self._t_prev, self._t_now = t, t
        self._load_all()
    # ----- lifecycle -----
    def set_action(self, a: int):
        self._action = max(0, min(a, len(self._frames) - 1))
        # clamp frame to available frames for new action
        frames_len = len(self._frames[self._action]) if self._frames and self._frames[self._action] else 1
        self._frame = 0 if frames_len == 0 else (self._frame % frames_len)
        # assume last in list is death by convention
        if self._action == len(self.actions) - 1: self._frame = 0
    def reset_frame(self): self._frame = 0
    def update(self):
        self._t_now = pg.time.get_ticks()
        if self._t_now - self._t_prev >= self.cooldown:
            frames_len = len(self._frames[self._action]) if self._frames and self._frames[self._action] else 1
            self._frame = 0 if frames_len == 0 else (self._frame + 1) % frames_len
            self._t_prev = self._t_now
    # ----- queries ----
    def is_last_frame(self) -> bool:
        frames = self._frames[self._action]
        return bool(frames) and self._frame == len(frames) - 1
    def surface(self) -> pg.Surface:
        frames = self._frames[self._action]
        if not frames:
            # fallback to a minimal transparent surface
            return pg.Surface((1, 1), pg.SRCALPHA)
        idx = self._frame if self._frame < len(frames) else 0
        return frames[idx]
    def last_surface_of(self, a: int) -> pg.Surface: return self._frames[a][-1]
    # ----- render -----
    def draw_centered(self, target: pg.Surface, reserved_bottom=0, top_margin=0):
        surf = self.surface()
        x = (target.get_width() - surf.get_width()) // 2
        y_avail = target.get_height() - reserved_bottom
        y = (y_avail - surf.get_height()) // 2 + top_margin
        target.blit(surf, (x, y))
    def draw_last_centered(self, target: pg.Surface, a: int, reserved_bottom=0, top_margin=0):
        surf = self.last_surface_of(a)
        x = (target.get_width() - surf.get_width()) // 2
        y_avail = target.get_height() - reserved_bottom
        y = (y_avail - surf.get_height()) // 2 + top_margin
        target.blit(surf, (x, y))
    # ----- internals -----
    def _load_all(self):
        for act in self.actions:
            sheet = self._load_image(f"static/{self.name}-{act}.png")
            # orientation: 1 => walk along height; 0 => along width (match legacy logic)
            total = sheet.get_height() // self.h if self.orient == 1 else sheet.get_width() // self.w
            frames = []
            for i in range(total):
                surf = pg.Surface((self.w, self.h)).convert_alpha()
                area_w = 0 if self.orient == 1 else (self.w * i)
                area_h = 0 if self.orient == 0 else (self.h * i)
                surf.blit(sheet, (0, 0), (area_w, area_h, self.w, self.h))
                if self.fill_width:
                    target_height = 400
                    ratio = self.w / self.h
                    new_h = min(target_height, 400)
                    new_w = int(new_h * ratio)
                    surf = pg.transform.scale(surf, (new_w, new_h))
                else: surf = pg.transform.scale(surf, (int(self.w * self.scale), int(self.h * self.scale)))
                surf.set_colorkey(self.colorkey)
                frames.append(surf)
            self._frames.append(frames)
    @staticmethod
    def _load_image(path: str) -> pg.Surface: return pg.image.load(path).convert_alpha()

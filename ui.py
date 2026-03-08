import pygame as pg
import time


class Colors:
    BG = (250, 250, 250)
    BORDER = (0, 0, 0)
    TEXT_DEFAULT = (20, 20, 20)
    TEXT_DIM = (150, 150, 150)
    EVE = (30, 130, 50)
    USER = (50, 50, 200)
    SYSTEM = (180, 100, 0)
    ERROR = (200, 50, 50)


def wrap_text(text: str, font: pg.font.Font, max_width: int):
    """Wrap text to fit inside a given width."""
    lines = []
    # Preserve explicit newlines
    paragraphs = text.split("\n")

    for paragraph in paragraphs:
        words = paragraph.split(" ")
        current_line = []

        for word in words:
            # Check width of line with new word
            test_line = " ".join(current_line + [word])
            width, _ = font.size(test_line)

            if width <= max_width:
                current_line.append(word)
            else:
                # If a single word is too long, we just have to break it or push it
                if not current_line:
                    lines.append(word)
                else:
                    lines.append(" ".join(current_line))
                    current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

    return lines


class ChatUI:
    def __init__(self, surface: pg.Surface, font_size=14):
        self.surface = surface
        self.font = None
        self.font_size = font_size
        self.messages = []  # List of tuples (text, color)

        # Input state
        self.input_lines = [""]
        self.active = False
        self.scroll_y = 0  # Pixel offset for scrolling
        self.max_scroll = 0
        self.is_scrolling = False
        self.is_typing = False

        self.init_font()
        # Initialize clipboard if supported
        try:
            pg.scrap.init()
        except Exception:
            pass

    def init_font(self):
        if not self.font:
            pg.font.init()
            try:
                # Clean modern fonts
                self.font = pg.font.SysFont(
                    "helvetica, arial, sans-serif", self.font_size
                )
            except:
                self.font = pg.font.Font(None, self.font_size)
        self.line_height = self.font.get_linesize()

    def add_message(self, text: str, sender: str = "system"):
        color = Colors.TEXT_DEFAULT
        if sender == "eve":
            color = Colors.EVE
        elif sender == "user":
            color = Colors.USER
        elif sender == "system":
            color = Colors.SYSTEM
        elif sender == "error":
            color = Colors.ERROR

        # We store the raw text and color, wrapping will be calculated dynamically on draw
        # to support window resizing!
        self.messages.append({"text": text, "color": color})
        # Auto scroll to bottom when new message arrives
        self.scroll_y = 999999

    def set_typing(self, typing: bool):
        self.is_typing = typing
        # Scroll to bottom if typing state changes to ensure we see the indicator
        if typing:
            self.scroll_y = 999999

    def remove_last_message(self):
        if self.messages:
            self.messages.pop()

    def handle_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEWHEEL:
            # Scroll chat history
            self.scroll_y -= event.y * 20
            self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))
            return None

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_RETURN:
                if pg.key.get_mods() & pg.KMOD_SHIFT:
                    # Add newline
                    self.input_lines.append("")
                else:
                    # Send message
                    full_text = "\n".join(self.input_lines).strip()
                    if full_text:
                        self.add_message(f"You: {full_text}", "user")
                        self.input_lines = [""]
                        return full_text
                    self.input_lines = [""]

            elif event.key == pg.K_BACKSPACE:
                if len(self.input_lines[-1]) > 0:
                    self.input_lines[-1] = self.input_lines[-1][:-1]
                elif len(self.input_lines) > 1:
                    # Merge with previous line
                    self.input_lines.pop()

            elif event.key == pg.K_v and (
                pg.key.get_mods() & pg.KMOD_CTRL or pg.key.get_mods() & pg.KMOD_META
            ):
                # Paste from clipboard
                try:
                    text = pg.scrap.get(pg.SCRAP_TEXT)
                    if text:
                        # Clean null bytes and decode
                        text = text.replace(b"\x00", b"").decode("utf-8")
                        lines = text.split("\n")
                        self.input_lines[-1] += lines[0]
                        self.input_lines.extend(lines[1:])
                except Exception as e:
                    print(f"Paste error: {e}")

            elif (
                event.key == pg.K_t
                and not self.active
                and not (pg.key.get_mods() & pg.KMOD_CTRL)
            ):
                self.active = True
                return None
            elif event.key == pg.K_ESCAPE:
                self.active = False
            else:
                if (
                    self.active
                    and event.unicode
                    and event.unicode.isprintable()
                    and event.key != pg.K_RETURN
                ):
                    self.input_lines[-1] += event.unicode
        return None

    def draw(self, rect: pg.Rect):
        if not self.font:
            return

        chat_x, chat_y, chat_w, chat_h = rect.x, rect.y, rect.width, rect.height
        padding = 15

        # Background
        pg.draw.rect(self.surface, Colors.BG, rect)
        # Right border
        pg.draw.line(
            self.surface,
            Colors.BORDER,
            (chat_x + chat_w - 1, chat_y),
            (chat_x + chat_w - 1, chat_y + chat_h),
            1,
        )

        # 1. Calculate Input Area Height
        # Wrap input lines to see how tall the input box needs to be
        wrapped_input = []
        for line in self.input_lines:
            wrapped = wrap_text(line, self.font, chat_w - padding * 2)
            if not wrapped:
                wrapped = [""]  # Empty line
            wrapped_input.extend(wrapped)

        # Max 5 lines for input box before it stops growing visually
        visible_input_lines = min(max(1, len(wrapped_input)), 5)
        input_h = (visible_input_lines * self.line_height) + (padding * 2)
        input_y = chat_y + chat_h - input_h

        # Top border of input box
        pg.draw.line(
            self.surface,
            Colors.BORDER,
            (chat_x, input_y),
            (chat_x + chat_w, input_y),
            1,
        )

        # 2. Draw Messages (History)
        history_h = chat_h - input_h
        history_rect = pg.Rect(chat_x, chat_y, chat_w, history_h)

        # We need to clip drawing so text doesn't spill over the input box or top
        self.surface.set_clip(history_rect)

        # Calculate total height of all wrapped messages
        wrapped_messages = []
        total_msg_height = 0
        for msg in self.messages:
            lines = wrap_text(msg["text"], self.font, chat_w - padding * 2)
            h = len(lines) * self.line_height
            wrapped_messages.append(
                {"lines": lines, "color": msg["color"], "height": h}
            )
            total_msg_height += h + (
                self.line_height // 2
            )  # Add spacing between messages

        # Calculate max scroll
        if self.is_typing:
            total_msg_height += self.line_height + (self.line_height // 2)

        self.max_scroll = max(0, total_msg_height - history_h + padding)
        # Clamp current scroll
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

        # Draw text based on scroll
        current_y = chat_y + padding - self.scroll_y
        for msg in wrapped_messages:
            # Optimization: only render if visible
            if current_y + msg["height"] > chat_y and current_y < chat_y + history_h:
                for line in msg["lines"]:
                    surf = self.font.render(line, True, msg["color"])
                    self.surface.blit(surf, (chat_x + padding, current_y))
                    current_y += self.line_height
            else:
                current_y += msg["height"]

            current_y += self.line_height // 2  # Spacing

        if self.is_typing:
            if current_y + self.line_height > chat_y and current_y < chat_y + history_h:
                surf = self.font.render("Eve is typing...", True, Colors.TEXT_DIM)
                self.surface.blit(surf, (chat_x + padding, current_y))

        self.surface.set_clip(None)  # Reset clip

        # 3. Draw Input Area
        input_text_y = input_y + padding

        if self.active:
            # Draw cursor
            cursor = "_" if time.time() % 1.0 < 0.5 else " "
            # We only show the last 'visible_input_lines' if text is too long
            display_lines = wrapped_input[-visible_input_lines:]

            for i, line in enumerate(display_lines):
                # Add cursor to the last line
                is_last = i == len(display_lines) - 1
                text_to_render = f"> {line}{cursor}" if is_last else f"  {line}"
                if i == 0 and len(display_lines) == 1:
                    text_to_render = f"> {line}{cursor}"
                elif i == 0:
                    text_to_render = f"> {line}"

                surf = self.font.render(text_to_render, True, Colors.TEXT_DEFAULT)
                self.surface.blit(surf, (chat_x + padding, input_text_y))
                input_text_y += self.line_height
        else:
            surf = self.font.render("Press 'T' to chat", True, Colors.TEXT_DIM)
            self.surface.blit(surf, (chat_x + padding, input_text_y))

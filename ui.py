import pygame as pg
import time


class Colors:
    BG = (255, 255, 255)  # TCI uses stark, pure white backgrounds
    BORDER = (0, 0, 0)  # Sharp black borders
    TEXT_DEFAULT = (0, 0, 0)  # TCI relies on pure black text
    TEXT_DIM = (150, 150, 150)  # Subdued grey for hints

    # We strip out the neon colors to match TCI's monochromatic vibe
    # We will differentiate users using bold prefixes rather than rainbow colors
    EVE = (0, 0, 0)
    USER = (0, 0, 0)
    SYSTEM = (100, 100, 100)  # System messages slightly grey
    ERROR = (200, 0, 0)  # Errors can stay red for visibility


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
    def __init__(self, surface: pg.Surface, font_size=18):
        self.surface = surface
        self.font = None
        self.font_bold = None
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
                # TCI uses clean, legible serif or sans-serif (usually system default sans-serif like Helvetica or Arial)
                # But they rely on whitespace and sizing.
                self.font = pg.font.SysFont(
                    "helvetica, arial, sans-serif", self.font_size
                )
                self.font_bold = pg.font.SysFont(
                    "helvetica, arial, sans-serif", self.font_size, bold=True
                )
            except:
                self.font = pg.font.Font(None, self.font_size)
                self.font_bold = pg.font.Font(None, self.font_size)
                self.font_bold.set_bold(True)
        # TCI has extremely generous line height (often 1.5x to 2x)
        self.line_height = int(self.font.get_linesize() * 1.6)

    def add_message(self, text: str, sender: str = "system"):
        color = Colors.TEXT_DEFAULT

        # Determine prefix and bold rendering requirement based on sender
        prefix = ""
        if sender == "eve":
            prefix = "Eve: "
            text = text.replace(
                "WhiteCar: ", ""
            )  # clean up backend prefix if it exists
        elif sender == "user":
            prefix = "You: "
            text = text.replace("You: ", "")

        elif sender == "system":
            color = Colors.SYSTEM
        elif sender == "error":
            color = Colors.ERROR

        # We store the raw text, color, and prefix
        self.messages.append(
            {"text": text, "prefix": prefix, "color": color, "sender": sender}
        )
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

        # TCI has massive padding/margins
        padding_x = 35
        padding_y = 40

        # Background
        pg.draw.rect(self.surface, Colors.BG, rect)

        # Right border - TCI uses very thin, elegant black lines, or sometimes no lines at all,
        # but a 1px solid black border is a good architectural divider
        pg.draw.line(
            self.surface,
            Colors.BORDER,
            (chat_x + chat_w - 1, chat_y),
            (chat_x + chat_w - 1, chat_y + chat_h),
            1,
        )

        # 1. Calculate Input Area Height
        wrapped_input = []
        for line in self.input_lines:
            # Wrap based on font
            wrapped = wrap_text(line, self.font, chat_w - (padding_x * 2))
            if not wrapped:
                wrapped = [""]
            wrapped_input.extend(wrapped)

        visible_input_lines = min(max(1, len(wrapped_input)), 5)
        # Input area padding is slightly tighter
        input_h = (visible_input_lines * self.font.get_linesize()) + 40
        input_y = chat_y + chat_h - input_h

        # Top border of input box - sharp 1px line
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

        self.surface.set_clip(history_rect)

        wrapped_messages = []
        total_msg_height = 0

        for msg in self.messages:
            # If it has a prefix (like "Eve: "), we need to account for it in the first line
            # TCI often uses bold for names and normal for body
            prefix = msg.get("prefix", "")
            prefix_w, _ = self.font_bold.size(prefix) if prefix else (0, 0)

            # We must wrap text considering the prefix on the first line
            # Pygame text rendering doesn't natively support mixing bold/normal on one line easily,
            # so we just render the prefix, then the text.
            # For wrapping, we just subtract the prefix width from the first line's max width.

            paragraphs = msg["text"].split("\n")
            lines_data = []  # List of tuples: (text, is_first_line)

            for p_idx, paragraph in enumerate(paragraphs):
                words = paragraph.split(" ")
                current_line = []

                for word in words:
                    test_line = " ".join(current_line + [word])
                    # If it's the very first line of the message, account for the bold prefix width
                    is_first = p_idx == 0 and not current_line and not lines_data
                    first_line_offset = (
                        prefix_w if (p_idx == 0 and len(lines_data) == 0) else 0
                    )

                    width, _ = self.font.size(test_line)

                    if width + first_line_offset <= (chat_w - padding_x * 2):
                        current_line.append(word)
                    else:
                        if not current_line:
                            lines_data.append(" ".join([word]))
                        else:
                            lines_data.append(" ".join(current_line))
                            current_line = [word]
                if current_line:
                    lines_data.append(" ".join(current_line))

            # Calculate height using the TCI generous line_height
            h = len(lines_data) * self.line_height
            # Add huge paragraph spacing (TCI style)
            total_msg_height += h + (self.line_height)

            wrapped_messages.append(
                {
                    "lines": lines_data,
                    "color": msg["color"],
                    "height": h,
                    "prefix": prefix,
                }
            )

        if self.is_typing:
            total_msg_height += self.line_height + (self.line_height)

        self.max_scroll = max(0, total_msg_height - history_h + padding_y)
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

        # Render the text
        current_y = chat_y + padding_y - self.scroll_y
        for msg in wrapped_messages:
            if current_y + msg["height"] > chat_y and current_y < chat_y + history_h:
                for i, line in enumerate(msg["lines"]):
                    # Render prefix if it's the very first line
                    offset_x = 0
                    if i == 0 and msg["prefix"]:
                        prefix_surf = self.font_bold.render(
                            msg["prefix"], True, Colors.TEXT_DEFAULT
                        )
                        self.surface.blit(prefix_surf, (chat_x + padding_x, current_y))
                        offset_x = prefix_surf.get_width()

                    # Render the body text
                    surf = self.font.render(line, True, msg["color"])
                    self.surface.blit(surf, (chat_x + padding_x + offset_x, current_y))
                    current_y += self.line_height
            else:
                current_y += msg["height"]

            current_y += self.line_height  # TCI huge margin between messages

        if self.is_typing:
            if current_y + self.line_height > chat_y and current_y < chat_y + history_h:
                surf = self.font.render("Eve is typing...", True, Colors.TEXT_DIM)
                self.surface.blit(surf, (chat_x + padding_x, current_y))

        self.surface.set_clip(None)

        # 3. Draw Input Area
        input_text_y = input_y + 20

        if self.active:
            cursor = "_" if time.time() % 1.0 < 0.5 else " "
            display_lines = wrapped_input[-visible_input_lines:]

            for i, line in enumerate(display_lines):
                is_last = i == len(display_lines) - 1
                # TCI uses minimal UI, so just a subtle cursor, no ">" prompt
                text_to_render = f"{line}{cursor}" if is_last else line

                surf = self.font.render(text_to_render, True, Colors.TEXT_DEFAULT)
                self.surface.blit(surf, (chat_x + padding_x, input_text_y))
                input_text_y += self.font.get_linesize()
        else:
            surf = self.font.render(
                "Click here or press 'T' to reply...", True, Colors.TEXT_DIM
            )
            self.surface.blit(surf, (chat_x + padding_x, input_text_y))

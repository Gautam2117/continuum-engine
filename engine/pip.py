"""Low Battery's original stick character and living-room staging."""
import math

from PIL import Image, ImageDraw

ACTIONS = ("notice", "reach", "slip", "reset")


def pip(ctx, duration, show, words):
    from .scenes import FPS

    width, height = ctx.W, ctx.H
    scale = min(width / 540, height / 750)
    offset_x, offset_y = (width - 540 * scale) / 2, (height - 750 * scale) / 2

    def point(x, y):
        return round(offset_x + x * scale), round(offset_y + y * scale)

    def box(x, y, right, bottom):
        return (*point(x, y), *point(right, bottom))

    room = Image.new("RGB", (width, height), "#191625")
    backdrop = ImageDraw.Draw(room)
    backdrop.rectangle(box(0, 533, 540, 750), fill="#2a2235")
    backdrop.rounded_rectangle(box(48, 378, 315, 552), round(28 * scale), fill="#53445e")
    backdrop.rounded_rectangle(box(61, 470, 335, 532), round(19 * scale), fill="#796384")
    backdrop.rectangle(box(387, 450, 500, 468), fill="#82685b")
    backdrop.rectangle(box(409, 468, 421, 546), fill="#82685b")
    backdrop.rectangle(box(472, 468, 484, 546), fill="#82685b")
    backdrop.line([point(445, 220), point(445, 441)], fill="#ac8876", width=round(5 * scale))
    backdrop.polygon([point(411, 220), point(479, 220), point(506, 302), point(384, 302)], fill="#f5b878")
    action = show["action"]

    for index in range(max(1, math.ceil(duration * FPS))):
        progress = min(1, index / max(1, duration * FPS - 1))
        beat = math.sin(math.pi * progress) ** 2
        lean = {"notice": 9, "reach": 63, "slip": -26, "reset": 13}[action] * beat
        arm = {"notice": 24, "reach": 141, "slip": 134, "reset": 53}[action] * beat
        phone_x = 399 + (52 * progress if action == "slip" else 52 if show.get("phone") in ("far", "dead") else 0)
        frame = room.copy()
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle(box(phone_x, 433, phone_x + 36, 447), max(1, round(4 * scale)), fill="#352d41" if show.get("phone") == "dead" else "#e69f84")
        ink = "#fff0da"
        stroke = max(1, round(6 * scale))
        shoulder = (206 + lean, 401)
        draw.line([point(199, 483), point(*shoulder), point(206 + lean, 365)], fill=ink, width=stroke, joint="curve")
        draw.line([point(199, 483), point(260, 481), point(276, 531)], fill=ink, width=stroke, joint="curve")
        draw.line([point(*shoulder), point(251 + lean, 444 - arm / 4), point(259 + lean + arm, 453 - arm / 9)], fill=ink, width=stroke, joint="curve")
        draw.ellipse(box(169 + lean, 305, 245 + lean, 381), fill="#211b2c", outline=ink, width=stroke)
        draw.line([point(179 + lean, 365), point(232 + lean, 365)], fill="#f5b878", width=stroke)
        draw.ellipse(box(224 + lean, 336, 231 + lean, 343), fill=ink)
        yield frame

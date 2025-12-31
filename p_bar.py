import time
import math
import os
from pyrogram.errors import FloodWait

class Timer:
    def __init__(self, time_between=5):
        self.start_time = time.time()
        self.time_between = time_between

    def can_send(self):
        if time.time() > (self.start_time + self.time_between):
            self.start_time = time.time()
            return True
        return False


from datetime import datetime,timedelta

#lets do calculations
def hrb(value, digits= 2, delim= "", postfix=""):
    """Return a human-readable file size.
    """
    if value is None:
        return None
    chosen_unit = "B"
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        if value > 1000:
            value /= 1024
            chosen_unit = unit
        else:
            break
    return f"{value:.{digits}f}" + delim + chosen_unit + postfix

def hrt(seconds, precision = 0):
    """Return a human-readable time delta as a string.
    """
    pieces = []
    value = timedelta(seconds=seconds)
    

    if value.days:
        pieces.append(f"{value.days}d")

    seconds = value.seconds

    if seconds >= 3600:
        hours = int(seconds / 3600)
        pieces.append(f"{hours}h")
        seconds -= hours * 3600

    if seconds >= 60:
        minutes = int(seconds / 60)
        pieces.append(f"{minutes}m")
        seconds -= minutes * 60

    if seconds > 0 or not pieces:
        pieces.append(f"{seconds}s")

    if not precision:
        return "".join(pieces)

    return "".join(pieces[:precision])



timer = Timer()

# designed by Mendax
async def progress_bar(current, total, reply, start):
    if timer.can_send():
        now = time.time()
        diff = now - start
        if diff < 1:
            return
        else:
            perc = f"{current * 100 / total:.1f}%"  # Percentage of progress
            elapsed_time = round(diff)
            speed = current / elapsed_time  # Speed in bytes per second
            remaining_bytes = total - current
            if speed > 0:
                eta_seconds = remaining_bytes / speed  # Calculate remaining time
                eta = hrt(eta_seconds, precision=1)  # ETA in human-readable format
            else:
                eta = "-"  # If no speed, set ETA as '-'
            sp = str(hrb(speed)) + "/s"  # Speed with units
            tot = hrb(total)  # Total size in human-readable format
            cur = hrb(current)  # Current size in human-readable format

            # Multicolor progress bar
            bar_length = 10
            completed_length = int(current * bar_length / total)
            remaining_length = bar_length - completed_length

            if completed_length == bar_length:
                progress_bar = "🟢" * bar_length  # Fully completed progress bar
            else:
                progress_bar = "🟢" * completed_length + "🔴" + "⚪" * (remaining_length - 1)  # Mixed progress bar

            try:
                await reply.edit(
                    f'╭─── 𝑼𝑷𝑳𝑶𝑨𝑫𝑰𝑵𝑮... ───╮\n'
                    f'┣ 𝑷𝑹𝑶𝑮𝑹𝑬𝑺𝑺 : {progress_bar}\n'
                    f'┣ ⚡ 𝑺𝑷𝑬𝑬𝑫 : {sp}\n'
                    f'┣ 📊 𝑷𝑬𝑹𝑪 : {perc}\n'
                    f'┣ 📂 𝑳𝑶𝑨𝑫𝑬𝑫 : {cur}\n'
                    f'┣ 💾 𝑻𝑶𝑻𝑨𝑳 : {tot}\n'
                    f'┣ ⏳ 𝑬𝑻𝑨 : {eta}\n'
                    f'╰── [🍃⏤͟͟͞͞ 𝗥ᴀᴅʜᴀ 𓆩♡𓆪 𝗞ʀɪꜱʜɴᴀ 🪈᪵᪳,](tg://user?id=7426949337) ──╯'
                )
            except FloodWait as e:
                time.sleep(e.x)  # Handle flood wait errors

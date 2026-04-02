import os
import sys
import platform
import subprocess


def run_game():
    bin_dir = os.path.join(os.path.dirname(__file__), 'bin')
    wad = os.path.join(os.path.dirname(__file__), 'doom1.wad')
    cfg = os.path.join(os.path.dirname(__file__), 'doom-ascii.cfg')

    if sys.platform == 'win32':
        machine = platform.machine().lower()
        binary = os.path.join(bin_dir, 'doom-ascii_win64.exe' if '64' in machine else 'doom-ascii_win32.exe')
    elif sys.platform == 'darwin':
        binary = os.path.join(bin_dir, 'doom-ascii_mac')
    else:
        binary = os.path.join(bin_dir, 'doom-ascii')

    os.chmod(binary, 0o755)

    if sys.platform == 'win32':
        import ctypes
        import msvcrt
        import time

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        conin = open('CONIN$', 'rb', buffering=0)
        conout = open('CONOUT$', 'wb', buffering=0)

        # Enable VT processing on the real console output handle
        conout_h = msvcrt.get_osfhandle(conout.fileno())
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(conout_h, ctypes.byref(mode))
        kernel32.SetConsoleMode(conout_h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING

        # Phase 1: attract/demo mode
        demo_proc = subprocess.Popen(
            [binary, '-iwad', wad, '-config', cfg],
            stdin=conin, stdout=conout, stderr=conout
        )

        # Wait for any key press.
        # GetAsyncKeyState reads hardware key state directly — it doesn't touch the
        # console input queue, so doom-ascii's ReadConsoleInput keeps working normally.
        IGNORE_VKS = {
            0x01, 0x02, 0x04, 0x05, 0x06,        # mouse buttons
            0x10, 0x11, 0x12,                      # Shift, Ctrl, Alt
            0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5,  # L/R Shift/Ctrl/Alt
        }
        key_pressed = False
        while demo_proc.poll() is None and not key_pressed:
            for vk in range(1, 0xFE):
                if vk not in IGNORE_VKS and user32.GetAsyncKeyState(vk) & 0x8000:
                    key_pressed = True
                    break
            if not key_pressed:
                time.sleep(0.033)

        if demo_proc.poll() is None:
            demo_proc.kill()
            demo_proc.wait()

        # Reset terminal state and flush any queued input before starting the game
        conout.write(b'\x1b[2J\x1b[H\x1b[0m\x1b[?25h')
        conout.flush()
        kernel32.FlushConsoleInputBuffer(msvcrt.get_osfhandle(conin.fileno()))

        # Phase 2: real game, E1M1, Normal skill
        subprocess.call(
            [binary, '-iwad', wad, '-config', cfg, '-warp', '1', '1', '-skill', '3'],
            stdin=conin, stdout=conout, stderr=conout
        )

        conin.close()
        conout.close()
    else:
        subprocess.call([binary, '-iwad', wad, '-config', cfg])

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

        conin  = open('CONIN$',  'rb', buffering=0)
        conout = open('CONOUT$', 'wb', buffering=0)
        conout_h = msvcrt.get_osfhandle(conout.fileno())
        conin_h  = msvcrt.get_osfhandle(conin.fileno())

        # Enable VT processing on the real console output
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(conout_h, ctypes.byref(mode))
        kernel32.SetConsoleMode(conout_h, mode.value | 0x0004)

        # Resize console buffer to 80x50 so there is no scrollback and
        # the game fills the entire visible area with no old content showing
        class COORD(ctypes.Structure):
            _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [('Left',  ctypes.c_short), ('Top',    ctypes.c_short),
                        ('Right', ctypes.c_short), ('Bottom', ctypes.c_short)]

        win = SMALL_RECT(0, 0, 79, 49)
        kernel32.SetConsoleWindowInfo(conout_h, True, ctypes.byref(win))
        kernel32.SetConsoleScreenBufferSize(conout_h, COORD(80, 50))

        # Phase 1: attract / demo mode
        demo_proc = subprocess.Popen(
            [binary, '-iwad', wad, '-config', cfg],
            stdin=conin, stdout=conout, stderr=conout
        )

        # Wait for any key press via GetAsyncKeyState (doesn't consume
        # console input events, so doom-ascii's ReadConsoleInput still works)
        IGNORE_VKS = {
            0x01, 0x02, 0x04, 0x05, 0x06,
            0x10, 0x11, 0x12,
            0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5,
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

        # Clear screen + scrollback, flush any queued input
        conout.write(b'\x1b[2J\x1b[3J\x1b[H\x1b[?25h\x1b[0m')
        conout.flush()
        kernel32.FlushConsoleInputBuffer(conin_h)

        # Phase 2: real game, E1M1, Normal skill
        subprocess.call(
            [binary, '-iwad', wad, '-config', cfg, '-warp', '1', '1', '-skill', '3'],
            stdin=conin, stdout=conout, stderr=conout
        )

        conin.close()
        conout.close()
    else:
        subprocess.call([binary, '-iwad', wad, '-config', cfg])

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
        print('YOU ARE LINUX!')
        binary = os.path.join(bin_dir, 'doom-ascii')

    if sys.platform == 'darwin':
        subprocess.run(
            ['xattr', '-d', 'com.apple.quarantine', binary],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    os.chmod(binary, 0o755)

    if sys.platform == 'win32':
        import ctypes
        import msvcrt
        import time
        import threading

        kernel32 = ctypes.windll.kernel32
        user32   = ctypes.windll.user32

        conin    = open('CONIN$',  'rb', buffering=0)
        conout   = open('CONOUT$', 'wb', buffering=0)
        conout_h = msvcrt.get_osfhandle(conout.fileno())
        conin_h  = msvcrt.get_osfhandle(conin.fileno())

        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(conout_h, ctypes.byref(mode))
        kernel32.SetConsoleMode(conout_h, mode.value | 0x0004)

        class COORD(ctypes.Structure):
            _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]
        class SMALL_RECT(ctypes.Structure):
            _fields_ = [('Left',  ctypes.c_short), ('Top',    ctypes.c_short),
                        ('Right', ctypes.c_short), ('Bottom', ctypes.c_short)]
        kernel32.SetConsoleScreenBufferSize(conout_h, COORD(80, 50))
        kernel32.SetConsoleWindowInfo(
            conout_h, True, ctypes.byref(SMALL_RECT(0, 0, 79, 49))
        )

        # INPUT_RECORD layout (matches Windows SDK, 20 bytes total)
        class _UChar(ctypes.Union):
            _fields_ = [('UnicodeChar', ctypes.c_wchar),
                        ('AsciiChar',   ctypes.c_char)]
        class _KeyEvent(ctypes.Structure):
            _fields_ = [('bKeyDown',          ctypes.c_int),
                        ('wRepeatCount',       ctypes.c_ushort),
                        ('wVirtualKeyCode',    ctypes.c_ushort),
                        ('wVirtualScanCode',   ctypes.c_ushort),
                        ('uChar',              _UChar),
                        ('dwControlKeyState',  ctypes.c_ulong)]
        class _EventUnion(ctypes.Union):
            _fields_ = [('KeyEvent', _KeyEvent), ('_pad', ctypes.c_byte * 16)]
        class INPUT_RECORD(ctypes.Structure):
            _fields_ = [('EventType', ctypes.c_ushort),
                        ('_align',    ctypes.c_ushort),
                        ('Event',     _EventUnion)]

        KEY_EVENT = 0x0001

        GAME_KEYS = [
            (0x57, 17, 'w'), (0x41, 30, 'a'),  # W, A
            (0x53, 31, 's'), (0x44, 32, 'd'),  # S, D
            (0x20, 57, ' '), (0x45, 18, 'e'),  # Space, E
            (0x4A, 36, 'j'), (0x4B, 37, 'k'),  # J, K
        ]

        def key_injector(stop_evt):
            prev_pressed = set()
            while not stop_evt.is_set():
                curr_pressed = set()
                for vk, scan, ch in GAME_KEYS:
                    if user32.GetAsyncKeyState(vk) & 0x8000:
                        curr_pressed.add(vk)
                records = []
                for vk, scan, ch in GAME_KEYS:
                    if vk in curr_pressed:
                        r = INPUT_RECORD()
                        r.EventType                       = KEY_EVENT
                        r.Event.KeyEvent.bKeyDown         = 1
                        r.Event.KeyEvent.wRepeatCount     = 1
                        r.Event.KeyEvent.wVirtualKeyCode  = vk
                        r.Event.KeyEvent.wVirtualScanCode = scan
                        r.Event.KeyEvent.uChar.UnicodeChar = ch
                        r.Event.KeyEvent.dwControlKeyState = 0
                        records.append(r)
                    elif vk in prev_pressed:
                        r = INPUT_RECORD()
                        r.EventType                       = KEY_EVENT
                        r.Event.KeyEvent.bKeyDown         = 0
                        r.Event.KeyEvent.wRepeatCount     = 1
                        r.Event.KeyEvent.wVirtualKeyCode  = vk
                        r.Event.KeyEvent.wVirtualScanCode = scan
                        r.Event.KeyEvent.uChar.UnicodeChar = ch
                        r.Event.KeyEvent.dwControlKeyState = 0
                        records.append(r)
                prev_pressed = curr_pressed
                # flush stale queued events so DOWN events can't pile up
                kernel32.FlushConsoleInputBuffer(conin_h)
                if records:
                    buf     = (INPUT_RECORD * len(records))(*records)
                    written = ctypes.c_ulong()
                    kernel32.WriteConsoleInputW(conin_h, buf, len(records),
                                               ctypes.byref(written))
                time.sleep(0.010)

        #DEMO MODE
        IGNORE_VKS = {0x01, 0x02, 0x04, 0x05, 0x06,
                      0x10, 0x11, 0x12,
                      0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}

        demo_proc = subprocess.Popen(
            [binary, '-iwad', wad, '-config', cfg],
            stdin=conin, stdout=conout, stderr=conout,
            cwd=os.path.dirname(binary)
        )
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

        conout.write(b'\x1b[2J\x1b[3J\x1b[H\x1b[?25h\x1b[0m')
        conout.flush()
        kernel32.FlushConsoleInputBuffer(conin_h)

        #GAME MODE
        stop_evt = threading.Event()
        injector = threading.Thread(target=key_injector, args=(stop_evt,), daemon=True)
        injector.start()
        try:
            subprocess.call(
                [binary, '-iwad', wad, '-config', cfg,
                 '-warp', '1', '1', '-skill', '3'],
                stdin=conin, stdout=conout, stderr=conout,
                cwd=os.path.dirname(binary)
            )
        finally:
            stop_evt.set()
            injector.join(timeout=1.0)

        conin.close()
        conout.close()

    else:
        import termios
        import tty as tty_module
        import select
        import time

        tty = open('/dev/tty', 'r+b', buffering=0)
        fd = tty.fileno()
        old_settings = termios.tcgetattr(fd)
        tty_module.setcbreak(fd, termios.TCSANOW)

        # Enter alternate screen so the game doesn't affect terminal scroll position
        tty.write(b'\x1b[?1049h')
        tty.flush()

        try:
            # DEMO MODE
            demo_proc = subprocess.Popen(
                [binary, '-iwad', wad, '-config', cfg],
                stdin=tty, stdout=tty, stderr=tty
            )
            key_pressed = False
            while demo_proc.poll() is None and not key_pressed:
                r, _, _ = select.select([fd], [], [], 0.033)
                if r:
                    key_pressed = True

            if demo_proc.poll() is None:
                demo_proc.kill()
                demo_proc.wait()

            tty.write(b'\x1b[2J\x1b[3J\x1b[H\x1b[?25h\x1b[0m')
            tty.flush()
            termios.tcflush(fd, termios.TCIFLUSH)

            # GAME MODE
            subprocess.call(
                [binary, '-iwad', wad, '-config', cfg,
                 '-warp', '1', '1', '-skill', '3'],
                stdin=tty, stdout=tty, stderr=tty
            )
        finally:
            # Exit alternate screen — terminal returns to exactly where it was
            tty.write(b'\x1b[?1049l')
            tty.flush()
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        tty.close()

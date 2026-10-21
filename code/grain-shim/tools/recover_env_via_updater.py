"""RECOVERY: run ONLY when the camera is in UPDATER mode, reached either through the pre-placed
\\updater\\mode recovery net (README, Deploy) or by forcing the BOOT_MODE_1 strap (bridge CL3005
(BOOT_MODE_1) -> CL3006 (EVER_3.15V) on SY-1013 Side B, next to CN3011).
Over USB (pmca updaterShellCommand): mount nflasha2 (=/setting), INSPECT, then revert env.txt ->
grain_hook_4a.so (the known-good logger) so the next NORMAL boot loads a harmless preload instead of
a bad grain_hook_4c.so. Inspect-first; the write is a single line.

    sudo -A env PYTHONPATH=$PMCA_RE python3 tools/recover_env_via_updater.py

PMCA_RE is a Sony-PMCA-RE checkout (the directory that holds config.py and the pmca package) and must be
importable, so it goes on PYTHONPATH. Needs pyusb. libusb is taken from LIBUSB_PATH (default
/opt/homebrew/lib/libusb-1.0.dylib); pass it through sudo with `env LIBUSB_PATH=... python3 ...`.
"""
import os, socket, threading, time
import usb.backend.libusb1 as b
LIBUSB = os.environ.get('LIBUSB_PATH', '/opt/homebrew/lib/libusb-1.0.dylib')
_o = b.get_backend
b.get_backend = lambda find_library=None: _o(find_library=lambda x: LIBUSB)
from pmca.commands.usb import updaterShellCommand
from pmca.platform.backend.usb import UsbPlatformBackend

def sh(be, cmds):
    a, bk = socket.socketpair()
    t = threading.Thread(target=be.interactiveShell, args=(a,), daemon=True); t.start()
    bk.settimeout(6); time.sleep(1.2)
    try:
        while True: bk.recv(65536)
    except Exception: pass
    res = []
    for i, c in enumerate(cmds):
        mk = '__M%d__' % i
        bk.sendall((c + ' ; echo ' + mk + '\n').encode())
        buf = b''; dl = time.time() + 15
        while mk.encode() not in buf and time.time() < dl:
            try: buf += bk.recv(65536)
            except socket.timeout: break
        res.append((c, buf.decode('latin1', 'replace')))
    try: bk.sendall(b'exit\n')
    except Exception: pass
    try: bk.close()
    except Exception: pass
    t.join(timeout=3)
    return res

def go(device):
    be = UsbPlatformBackend(device); be.start()
    try:
        print('===== 1) INSPECT =====')
        insp = sh(be, ['id', 'ls /dev/nflash*', 'mkdir -p /setting',
                       'mount -t vfat -o rw /dev/nflasha2 /setting 2>&1',
                       'ls -la /setting', 'echo "--- env.txt ---"', 'cat /setting/env.txt',
                       'ls -la /setting/grain_hook_4a.so 2>&1', 'ls -la /setting/grain_hook_4c.so 2>&1'])
        for c, o in insp: print('#### %s\n%s' % (c, o))
        env = next((o for c, o in insp if c == 'cat /setting/env.txt'), '')
        ls4a = next((o for c, o in insp if c.startswith('ls -la /setting/grain_hook_4a')), '')
        have4a = 'grain_hook_4a.so' in ls4a and 'No such file' not in ls4a   # the error text also names the file
        if 'grain_hook_4a.so' not in env and not have4a:
            print('ABORT: 4a.so not found and env not reverted — inspect manually before writing.'); return
        print('===== 2) REVERT env.txt -> 4a.so =====')
        # echo, not printf: the updater busybox has no printf (stage-1 run: a printf redirect left the file EMPTY)
        wr = sh(be, ["echo 'LD_PRELOAD=/setting/grain_hook_4a.so' > /setting/env.txt",
                     'cat /setting/env.txt', 'sync'])
        for c, o in wr: print('#### %s\n%s' % (c, o))
        if 'LD_PRELOAD=/setting/grain_hook_4a.so' not in next((o for c, o in wr if c == 'cat /setting/env.txt'), ''):
            print('WARNING: env.txt does not read back as the 4a line; inspect it before any normal boot.')
        print('===== 3) VERIFY + UNMOUNT =====')
        for c, o in sh(be, ['cat /setting/env.txt', 'sync', 'umount /setting', 'sync', 'echo RECOVER_DONE']):
            print('#### %s\n%s' % (c, o))
    finally:
        try: be.stop()
        except Exception as e: print('stop:', e)

updaterShellCommand(complete=go)

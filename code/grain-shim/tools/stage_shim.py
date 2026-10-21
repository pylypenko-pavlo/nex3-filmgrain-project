"""Stage grain_hook_4c.so on the camera in the safe order and arm it. Camera in USB mass-storage mode;
the script switches it to service mode (senser) through Sony-PMCA-RE.

    sudo -A env PYTHONPATH=$PMCA_RE python3 tools/stage_shim.py --so grain_hook_4c.so \\
        --md5 $(md5sum grain_hook_4c.so | cut -c1-32)

PMCA_RE is a Sony-PMCA-RE checkout (the directory that holds config.py and the pmca package) and must be
importable, so it goes on PYTHONPATH. Needs pyusb. libusb is taken from LIBUSB_PATH (default
/opt/homebrew/lib/libusb-1.0.dylib); pass it through sudo with `env LIBUSB_PATH=... python3 ...`.

Why the order matters: env.txt names the preload that is loaded before anything else at boot, and a
missing or truncated .so kills userland. Overwriting the .so that env.txt still points at, with a USB
write that can fail half way, is how the development body was lost. So:

  0. local checks, before the camera is touched: --so is an ELF file and its md5 equals --md5
  1. print /setting/env.txt and /setting/mode/dmode; require dmode == b'3\\n' and a valid
     /setting/grain_hook_4a.so on the camera (deploy tools/grain_hook_4a.so first)
  2. DISARM: env.txt = LD_PRELOAD=/setting/grain_hook_4a.so, read back, compare
  3. write /setting/grain_hook_4c.so, read back, compare md5 with --md5; any failure stops here with the
     camera still on the harmless 4a logger
  4. truncate /setting/grain_hook_4c.log
  5. RE-ARM: env.txt = LD_PRELOAD=/setting/grain_hook_4c.so, read back, compare

The new env.txt takes effect on the next cold boot. Reading the log and disarming afterwards: disarm.py.
"""
import argparse
import hashlib
import io
import os
import re
import sys

try:
    import usb.backend.libusb1 as b
    from pmca.commands.usb import senserShellCommand
except ImportError as e:
    sys.exit('cannot import pyusb or pmca (%s). Put the Sony-PMCA-RE checkout on PYTHONPATH '
             '(PYTHONPATH=$PMCA_RE) and install its requirements (pyusb).' % e)

LIBUSB = os.environ.get('LIBUSB_PATH', '/opt/homebrew/lib/libusb-1.0.dylib')
_o = b.get_backend
b.get_backend = lambda find_library=None: _o(find_library=lambda x: LIBUSB)

ENV = '/setting/env.txt'
DMODE = '/setting/mode/dmode'
HOOK_4A = '/setting/grain_hook_4a.so'
HOOK_4C = '/setting/grain_hook_4c.so'
LOG_4C = '/setting/grain_hook_4c.log'
DISARM = b'LD_PRELOAD=/setting/grain_hook_4a.so\n'
ARM = b'LD_PRELOAD=/setting/grain_hook_4c.so\n'


class Abort(Exception):
    pass


def read_remote(cam, path):
    f = io.BytesIO()
    cam.readFile(path, f)
    return f.getvalue()


def show(cam, path):
    try:
        print('%s = %r' % (path, read_remote(cam, path)))
    except Exception as e:
        print('%s : %s' % (path, e))


def write_verified(cam, path, data):
    cam.writeFile(path, data)
    rb = read_remote(cam, path)
    if rb != data:
        raise Abort('read-back of %s differs: wrote %d B, read %d B (%r)' % (path, len(data), len(rb), rb[:80]))


def stage(cam, data, md5, state):
    print('--- 1. current boot config ---')
    show(cam, ENV)
    show(cam, DMODE)
    try:
        dmode = read_remote(cam, DMODE)
    except Exception as e:
        raise Abort('%s cannot be read (%s). env.txt is only parsed when dmode exists: write it first '
                    '(README, Deploy, first time on a body).' % (DMODE, e))
    if dmode != b'3\n':
        raise Abort('%s is %r, expected b"3\\n", the only form found safe. Fix it before staging.' % (DMODE, dmode))
    try:
        hook4a = read_remote(cam, HOOK_4A)
    except Exception as e:
        hook4a = b''
        print('%s : %s' % (HOOK_4A, e))
    if hook4a[:4] != b'\x7fELF':
        raise Abort('%s is missing or not an ELF file. Disarming points env.txt at it, so it must exist: '
                    'build and deploy tools/grain_hook_4a.so first (README, Deploy).' % HOOK_4A)
    print('%s: %d B md5 %s' % (HOOK_4A, len(hook4a), hashlib.md5(hook4a).hexdigest()))

    print('--- 2. DISARM: env.txt -> 4a logger ---')
    state[0] = 'env.txt write to the 4a logger unverified: check env.txt before any boot'
    write_verified(cam, ENV, DISARM)
    state[0] = 'disarmed, env.txt -> grain_hook_4a.so'
    print('env.txt = %r OK' % DISARM)

    print('--- 3. write %s ---' % HOOK_4C)
    state[0] = 'disarmed; grain_hook_4c.so is partial or unverified, which is harmless while disarmed'
    cam.writeFile(HOOK_4C, data)
    rb = read_remote(cam, HOOK_4C)
    got = hashlib.md5(rb).hexdigest()
    print('wrote %d B, read back %d B md5 %s (expected %s)' % (len(data), len(rb), got, md5))
    if got != md5:
        raise Abort('read-back md5 differs from --md5. Not arming.')
    state[0] = 'disarmed, grain_hook_4c.so verified'

    print('--- 4. truncate %s ---' % LOG_4C)
    cam.writeFile(LOG_4C, b'')

    print('--- 5. RE-ARM: env.txt -> 4c ---')
    state[0] = 're-arming'
    write_verified(cam, ENV, ARM)
    state[0] = 'armed, env.txt -> grain_hook_4c.so'
    print('env.txt = %r OK' % ARM)
    print('DONE: staged and armed. Cold boot now (battery pull), shoot, then read the log with tools/disarm.py.')


def main():
    ap = argparse.ArgumentParser(description='Stage and arm grain_hook_4c.so in the safe order.')
    ap.add_argument('--so', required=True, help='local grain_hook_4c.so to stage')
    ap.add_argument('--md5', required=True, help='expected md5 of --so (32 hex chars)')
    args = ap.parse_args()
    md5 = args.md5.strip().lower()
    if not re.fullmatch(r'[0-9a-f]{32}', md5):
        sys.exit('--md5 must be 32 hex characters')
    with open(args.so, 'rb') as f:
        data = f.read()
    got = hashlib.md5(data).hexdigest()
    print('local %s: %d B md5 %s (expected %s)' % (args.so, len(data), got, md5))
    if data[:4] != b'\x7fELF':
        sys.exit('ABORT: %s is not an ELF file' % args.so)
    if got != md5:
        sys.exit('ABORT: local md5 differs from --md5')

    state = ['no change yet']
    ok = [False]
    called = [False]

    def go(cam):
        called[0] = True
        try:
            stage(cam, data, md5, state)
            ok[0] = True
        except Abort as e:
            print('ABORT: %s' % e)
        except Exception as e:
            print('ERROR: %s: %s' % (type(e).__name__, e))
        if not ok[0]:
            if state[0] == 're-arming':
                try:
                    write_verified(cam, ENV, DISARM)
                    state[0] = 'disarmed, env.txt -> grain_hook_4a.so (restored after a failed re-arm)'
                except Exception as e:
                    state[0] = 're-arm failed and env.txt could not be restored (%s): check env.txt before any boot' % e
            print('camera state: %s' % state[0])

    senserShellCommand(complete=go)
    if not called[0]:
        print('no senser session was opened; nothing was written to the camera')
    if not ok[0]:
        sys.exit(1)


if __name__ == '__main__':
    main()

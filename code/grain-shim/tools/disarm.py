"""Read the shim's log, then disarm: revert /setting/env.txt to the harmless 4a logger. Camera in USB
mass-storage mode; the script switches it to service mode (senser) through Sony-PMCA-RE.

    sudo -A env PYTHONPATH=$PMCA_RE python3 tools/disarm.py

PMCA_RE is a Sony-PMCA-RE checkout (the directory that holds config.py and the pmca package) and must be
importable, so it goes on PYTHONPATH. Needs pyusb. libusb is taken from LIBUSB_PATH (default
/opt/homebrew/lib/libusb-1.0.dylib); pass it through sudo with `env LIBUSB_PATH=... python3 ...`.

It prints /setting/grain_hook_4c.log, env.txt and mode/dmode, then writes
LD_PRELOAD=/setting/grain_hook_4a.so and reads it back. It refuses to write if /setting/grain_hook_4a.so is
missing or not an ELF file, because pointing env.txt at a missing preload kills userland at the next boot.
The change takes effect on the next cold boot. To re-arm, run stage_shim.py.
"""
import io
import os
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

HOOK_4A = '/setting/grain_hook_4a.so'
REVERT = b'LD_PRELOAD=/setting/grain_hook_4a.so\n'


def read_remote(cam, path):
    f = io.BytesIO()
    cam.readFile(path, f)
    return f.getvalue()


def go(cam):
    print('===== /setting/grain_hook_4c.log =====')
    try:
        print(read_remote(cam, '/setting/grain_hook_4c.log').decode('latin1', 'replace'))
    except Exception as e:
        print('(no log or read error: %s)' % e)
    print('===== current boot config =====')
    for p in ['/setting/env.txt', '/setting/mode/dmode']:
        try:
            print('%s = %r' % (p, read_remote(cam, p)))
        except Exception as e:
            print('%s : %s' % (p, e))
    try:
        hook4a = read_remote(cam, HOOK_4A)
    except Exception as e:
        hook4a = b''
        print('%s : %s' % (HOOK_4A, e))
    if hook4a[:4] != b'\x7fELF':
        print('ABORT: %s is missing or not an ELF file; env.txt left unchanged. Deploy tools/grain_hook_4a.so '
              'first (README, Deploy).' % HOOK_4A)
        return
    print('===== DISARM: env.txt -> 4a logger =====')
    cam.writeFile('/setting/env.txt', REVERT)
    rb = read_remote(cam, '/setting/env.txt')
    print('env.txt now = %r  %s' % (rb, 'OK' if rb == REVERT else 'MISMATCH'))
    if rb == REVERT:
        print('DISARMED: the next cold boot loads the harmless 4a logger.')
    else:
        print('NOT CONFIRMED: check env.txt before any boot.')


if __name__ == '__main__':
    senserShellCommand(complete=go)

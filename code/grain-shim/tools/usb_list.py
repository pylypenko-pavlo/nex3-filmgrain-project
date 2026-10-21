"""List every USB device libusb can see and classify the Sony ones. Run with sudo.

libusb is the authoritative camera check: it is what pmca uses. On macOS system_profiler and ioreg can
miss the camera even when it works, so a camera absent from those but present here is fine, and a camera
absent here is not enumerating.

Sony vendor 0x054c: updater PIDs 0x033a/0x03e2, senser (service mode) PIDs 0x02a9/0x0336. Any other Sony
PID is printed as another mode (for example mass storage).

Usage:  sudo env LIBUSB_PATH=/path/to/libusb python3 tools/usb_list.py
LIBUSB_PATH defaults to /opt/homebrew/lib/libusb-1.0.dylib. Needs pyusb.
"""
import os

import usb.backend.libusb1 as b
import usb.core
import usb.util

LIBUSB = os.environ.get('LIBUSB_PATH', '/opt/homebrew/lib/libusb-1.0.dylib')
_o = b.get_backend
b.get_backend = lambda find_library=None: _o(find_library=lambda x: LIBUSB)

SONY = 0x054c
UPD = [0x033a, 0x03e2]
SEN = [0x02a9, 0x0336]

n = 0
for dev in usb.core.find(find_all=True):
    n += 1
    man = prod = ''
    try:
        man = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else ''
    except Exception:
        pass
    try:
        prod = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else ''
    except Exception:
        pass
    tag = ''
    if dev.idVendor == SONY:
        tag = ' <<< SONY'
        if dev.idProduct in UPD:
            tag += ' UPDATER'
        elif dev.idProduct in SEN:
            tag += ' SENSER'
        else:
            tag += ' (other Sony mode PID=0x%04x)' % dev.idProduct
    print('VID %04x PID %04x  cls=%02x  %r / %r%s' % (dev.idVendor, dev.idProduct, dev.bDeviceClass, man, prod, tag))
print('total USB devices seen by libusb: %d' % n)

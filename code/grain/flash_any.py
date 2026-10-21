# usage: flash_any.py <image.bin> <device e.g. /dev/nflasha3> <recovery.bin>
# writes image to raw device via updater shell, md5-verifies whole device, restores recovery on mismatch,
# zeroes WBI (/dev/nflasha5) on success. Run inside updaterShellCommand.
import io,os,socket,threading,time,hashlib,re,sys
import usb.backend.libusb1 as b
_o=b.get_backend
b.get_backend=lambda find_library=None:_o(find_library=lambda x:os.environ.get('LIBUSB_PATH','/opt/homebrew/lib/libusb-1.0.dylib'))
from pmca.commands.usb import updaterShellCommand
from pmca.platform.backend.usb import UsbPlatformBackend
IMG=open(sys.argv[1],'rb').read(); DEV=sys.argv[2]; RECOV=open(sys.argv[3],'rb').read()
IMD5=hashlib.md5(IMG).hexdigest(); RMD5=hashlib.md5(RECOV).hexdigest(); NBLK=len(IMG)//65536
def sh(be,cmds,tmo=90):
    a,bk=socket.socketpair();t=threading.Thread(target=be.interactiveShell,args=(a,),daemon=True);t.start()
    bk.settimeout(tmo);time.sleep(1.0)
    try:
        while True: bk.recv(65536)
    except: pass
    out=[]
    for i,c in enumerate(cmds):
        mk='__M%d__'%i; bk.sendall((c+' ; echo '+mk+'\n').encode()); buf=b'';dl=time.time()+tmo+60
        while mk.encode() not in buf and time.time()<dl:
            try: buf+=bk.recv(65536)
            except socket.timeout: break
        out.append(buf.decode('latin1','replace'))
    try: bk.sendall(b'exit\n');bk.close()
    except: pass
    t.join(timeout=3); return out
def devmd5(be):
    o=sh(be,['dd if=%s bs=65536 count=%d 2>/dev/null | md5sum'%(DEV,NBLK)],tmo=120)[0]
    m=re.search(r'([0-9a-f]{32})',o); return (m.group(1) if m else None)
def go(device):
    be=UsbPlatformBackend(device); be.start()
    try:
        print('FLASH %s -> %s (%d bytes, md5 %s)'%(sys.argv[1],DEV,len(IMG),IMD5))
        be.writeFile(DEV, io.BytesIO(IMG)); sh(be,['sync'])
        got=devmd5(be); print('device md5=%s -> %s'%(got,'MATCH' if got==IMD5 else 'MISMATCH'))
        if got!=IMD5:
            print('RESTORING recovery'); be.writeFile(DEV, io.BytesIO(RECOV)); sh(be,['sync'])
            print('restore md5=%s -> %s'%(devmd5(be),'ok' if devmd5(be)==RMD5 else 'BAD'))
            print('ABORT, no WBI, no reboot'); return
        sh(be,['dd if=/dev/zero of=/dev/nflasha5 bs=512 count=1','sync'])
        print('FLASH VERIFIED + WBI zeroed. Safe to reboot.')
    finally:
        try: be.stop()
        except Exception as e: print('stop',e)
updaterShellCommand(complete=go)

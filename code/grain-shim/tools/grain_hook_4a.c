/* grain_hook_4a.c: harmless logger preload, the known-good .so that /setting/env.txt points at while a new grain_hook_4c.so is staged.
 * It only appends "CLOSE JPG <path> <size>" lines to /setting/grain_hook_4a.log. It builds with the same freestanding line as
 * grain_hook.c (README, Build) with output grain_hook_4a.so, and is deployed to the camera as /setting/grain_hook_4a.so. */
/* grain_hook_4a.c — Stage 4a: Fsys_Close/Fsys_Open interposer, DETECTION ONLY (no grain).
 *
 * Proves the hook fires exactly on SOOC-JPEG saves: when a DCF still "...\DSC*.JPG" is CLOSED,
 * append "CLOSE JPG <path> <size>" to /setting/grain_hook_4a.log. For EVERY other close it is a
 * pure transparent passthrough. The real Fsys_* is ALWAYS called with unchanged args and its value
 * returned unchanged; all logging is pure-additive and can never alter firmware behavior.
 *
 * FAIL-SAFE invariants:
 *  - Fsys_Open/Close forward to the real function FIRST and return its value UNCHANGED.
 *  - The real function is resolved via __dlopen("libInfraFsys.so")+__dlsym (NOT RTLD_NEXT: the camera
 *    sonyld's __dlsym returns NULL for -1/0/-2/-3; __dlopen(lib)+__dlsym is the proven route, and it
 *    bypasses our own exported symbol — verified in qemu).
 *  - Resolution is cached, lazy (only in processes that actually call Fsys_*), and sanity-checked
 *    (real != our own address). If resolution ever fails the interposer returns a benign error (-1);
 *    this MUST be proven not to happen via the isolated updater-shell test BEFORE any boot-path use
 *    (the ctor/first-call logs the resolved pointer).
 *  - The ONE unproven assumption (Fsys_Open arg1 == out-handle pointer) is used ONLY to populate a
 *    best-effort handle->path table for the CLOSE-time size log; a wrong assumption yields a wrong/no
 *    log, never a behavior change. It is guarded (only deref on success + matched JPG path) and must
 *    be confirmed in the zero-brick isolation test (a bad deref there crashes only the test process).
 *
 * Build: arm-linux-gnueabi-gcc -march=armv5te -shared -fPIC -nostdlib -o grain_hook_4a.so grain_hook_4a.c
 * ELF shape: 2 PT_LOAD + DT_INIT_ARRAY + 1 R_ARM_RELATIVE (same proven shape as grain_probe_fs.so).
 */

/* ---- raw Linux/ARM EABI syscalls (no libc) ---- */
static long sc(long n, long a, long b, long c){
    register long r7 __asm__("r7")=n, r0 __asm__("r0")=a, r1 __asm__("r1")=b, r2 __asm__("r2")=c;
    __asm__ volatile("svc #0":"+r"(r0):"r"(r7),"r"(r1),"r"(r2):"memory");
    return r0;
}
#define SYS_read   3
#define SYS_write  4
#define SYS_open   5
#define SYS_close  6
#define SYS_lseek  19
#define O_RDONLY   0
#define O_WRONLY   1
#define O_CREAT    0x40
#define O_APPEND   0x400
#define SEEK_END   2

/* ---- sonyld dynamic-resolution exports ---- */
extern void* __dlopen(const char* path, int mode);
extern void* __dlsym(void* handle, const char* name);

/* ---- tiny freestanding string helpers ---- */
static int slen(const char* s){ int n=0; if(!s) return 0; while(s[n]) n++; return n; }
static char lc(char c){ return (c>='A'&&c<='Z') ? (char)(c+32) : c; }
static int has_DSC(const char* s){
    for(int i=0; s[i]; i++)
        if(s[i]=='D'&&s[i+1]=='S'&&s[i+2]=='C') return 1;
    return 0;
}
static int ends_JPG(const char* s){
    int n=slen(s);
    if(n<4) return 0;
    return lc(s[n-4])=='.' && lc(s[n-3])=='j' && lc(s[n-2])=='p' && lc(s[n-1])=='g';
}
static int is_dcf_jpg(const char* p){
    return p && ends_JPG(p) && has_DSC(p);   /* "...\DSC#####.JPG" */
}
static int utoa(unsigned long v, char* out){
    char t[20]; int k=0; if(v==0){ out[0]='0'; return 1; }
    while(v){ t[k++]='0'+(int)(v%10); v/=10; }
    for(int i=0;i<k;i++) out[i]=t[k-1-i];
    return k;
}

/* ---- append one line to the log (self-contained open/write/close; never blocks on our own fd) ---- */
static void logline(const char* path, unsigned long size){
    int fd = (int)sc(SYS_open, (long)"/setting/grain_hook_4a.log", O_WRONLY|O_CREAT|O_APPEND, 0666);
    if(fd < 0) return;
    char buf[160]; int n=0;
    const char* pre="CLOSE JPG ";
    for(int i=0; pre[i]; i++) buf[n++]=pre[i];
    for(int i=0; path[i] && n<120; i++) buf[n++]=path[i];
    buf[n++]=' ';
    n += utoa(size, buf+n);
    buf[n++]='\n';
    sc(SYS_write, fd, (long)buf, n);
    sc(SYS_close, fd, 0, 0);
}
static void logmsg(const char* m){
    int fd=(int)sc(SYS_open,(long)"/setting/grain_hook_4a.log",O_WRONLY|O_CREAT|O_APPEND,0666);
    if(fd<0) return; sc(SYS_write,fd,(long)m,slen(m)); sc(SYS_close,fd,0,0);
}
static unsigned long filesize(const char* path){
    int fd=(int)sc(SYS_open,(long)path,O_RDONLY,0);
    if(fd<0) return 0;
    long sz=sc(SYS_lseek, fd, 0, SEEK_END);     /* off_t; stills are < 2 GB */
    sc(SYS_close,fd,0,0);
    return sz<0 ? 0UL : (unsigned long)sz;
}

/* ---- handle -> path table (best-effort; losing an entry only loses a log line) ---- */
#define NSLOT 32
#define PLEN  120
static struct { long h; char used; char path[PLEN]; } g_tab[NSLOT];
static void tab_put(long h, const char* p){
    int free=-1;
    for(int i=0;i<NSLOT;i++){ if(g_tab[i].used && g_tab[i].h==h){ free=i; break; } if(free<0 && !g_tab[i].used) free=i; }
    if(free<0) free=0;                           /* overwrite oldest-ish; never fail */
    g_tab[free].h=h; g_tab[free].used=1;
    int n=slen(p); if(n>=PLEN) n=PLEN-1;
    for(int i=0;i<n;i++) g_tab[free].path[i]=p[i]; g_tab[free].path[n]=0;
}
static const char* tab_take(long h){
    for(int i=0;i<NSLOT;i++) if(g_tab[i].used && g_tab[i].h==h){ g_tab[i].used=0; return g_tab[i].path; }
    return 0;
}

/* ---- cached real pointers (lazy, scoped, sanity-checked) ---- */
typedef long (*fsys_open_t)(long,long,long,long);
typedef long (*fsys_close_t)(long);
static fsys_open_t  g_open;
static fsys_close_t g_close;
static int g_tried;

long Fsys_Open(long a0,long a1,long a2,long a3);   /* fwd decls for self-address sanity */
long Fsys_Close(long h);

static void ensure_resolved(void){
    if(g_tried) return;
    g_tried=1;
    void* lib=__dlopen("libInfraFsys.so",1);       /* RTLD_LAZY=1; already loaded in appFw -> same handle */
    if(!lib){ logmsg("4a: dlopen(libInfraFsys) FAILED\n"); return; }
    void* ro=__dlsym(lib,"Fsys_Close");
    void* rp=__dlsym(lib,"Fsys_Open");
    if(ro==(void*)&Fsys_Close) ro=0;               /* never bind to ourselves */
    if(rp==(void*)&Fsys_Open)  rp=0;
    g_close=(fsys_close_t)ro;
    g_open =(fsys_open_t) rp;
    logmsg(g_close? "4a: resolved Fsys_Close OK\n" : "4a: resolve Fsys_Close NULL\n");
}

/* ======================= interposers ======================= */
long Fsys_Open(long a0,long a1,long a2,long a3){   /* Fsys_Open(path, outHandle*, flags, mode) */
    ensure_resolved();
    if(!g_open) return -1;                          /* gated: proven non-NULL in isolation before boot use */
    long r = g_open(a0,a1,a2,a3);                   /* real open, args unchanged */
    /* best-effort record for the CLOSE-time size log; guarded, additive */
    if(r>=0 && a1 && is_dcf_jpg((const char*)a0)){
        long handle = *(long*)a1;                   /* ASSUMPTION: arg1 = out-handle ptr (validate in isolation) */
        tab_put(handle, (const char*)a0);
    }
    return r;                                       /* unchanged */
}

long Fsys_Close(long h){
    ensure_resolved();
    if(!g_close) return -1;                          /* gated */
    long r = g_close(h);                             /* real close FIRST, unchanged */
    const char* p = tab_take(h);                     /* only matches handles we recorded as DCF-JPG */
    if(p){
        unsigned long sz = filesize(p);              /* file is complete on disk now */
        logline(p, sz);
    }
    return r;                                        /* unchanged */
}

/* ---- constructor: mark load (for isolation/boot confirmation); never crash/block ---- */
__attribute__((constructor)) static void grain_hook_4a_init(void){
    logmsg("4a: hook loaded\n");
}

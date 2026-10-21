/* grain_hook.c — Stage 4c grain shim (FAST landing, owner opted for speed over the .TMP backup; the camera
 * is a toy and the original isn't precious). On a fresh DCF-JPG save: interpose Fsys_Close, then
 *   read the source Exif header; CALLBACK-decode the source from the file (read_cb=Fsys_Read) + baked-tile
 *   grain + encode the grained JPEG into a RAM buffer (write_cb, Exif(APP1) spliced); the ORIGINAL is untouched
 *   during the whole (slow) codec. THEN land in one shot: Fsys_Remove(orig)+Fsys_Open(orig,0x7)+Fsys_Write.
 * NO .TMP: one write, ~2x less SD I/O; risk = a crash/power-loss in the ~1-2s write window loses the shot (the
 * codec runs with the original intact, so a watchdog reboot during compute does NOT lose it). Rename is dead.
 * Memory: ~6MB RAM encode buffer + decode scratch ~0.1MB + baked tile 256KB (rodata). Freestanding.
 * Build: arm-linux-gnueabi-gcc -march=armv5te -shared -fPIC -nostdlib -O2 -ffreestanding -fno-builtin
 *        -fno-tree-loop-distribute-patterns -o grain_hook_4c.so grain_hook.c swjpeg.c grain_stream.c grain_tile.S */
#include "swjpeg.h"
extern void grain_stream_init(void*,const jpeg_image*,unsigned,short*,unsigned long);
extern int  grain_stream_band(void*,jpeg_comp[3]);

static long sc(long n,long a,long b,long c){register long r7 __asm__("r7")=n,r0 __asm__("r0")=a,r1 __asm__("r1")=b,r2 __asm__("r2")=c;__asm__ volatile("svc #0":"+r"(r0):"r"(r7),"r"(r1),"r"(r2):"memory");return r0;}
static long sc6(long n,long a,long b,long c,long d,long e,long f){register long r7 __asm__("r7")=n,r0 __asm__("r0")=a,r1 __asm__("r1")=b,r2 __asm__("r2")=c,r3 __asm__("r3")=d,r4 __asm__("r4")=e,r5 __asm__("r5")=f;__asm__ volatile("svc #0":"+r"(r0):"r"(r7),"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5):"memory");return r0;}
#define SYS_gettimeofday 78
#define SYS_sysinfo 116
#define SYS_mmap2 192
#define SYS_munmap 91
#define SYS_openx 5
#define SYS_writex 4
#define SYS_closex 6
#define PROT_RW 3
#define MAP_ANON_PRIV 0x22
static void* xmmap(unsigned long len){ unsigned long r=(unsigned long)sc6(SYS_mmap2,0,len,PROT_RW,MAP_ANON_PRIV,-1,0); return (r<0xfffff000UL)?(void*)r:(void*)0; }
static void  xmunmap(void* p,unsigned long len){ if(p&&len) sc(SYS_munmap,(long)p,len,0); }

extern void* __dlopen(const char* p,int m);
extern void* __dlsym(void* h,const char* n);

static int slen(const char* s){int n=0;if(!s)return 0;while(s[n])n++;return n;}
static char lc(char c){return (c>='A'&&c<='Z')?(char)(c+32):c;}
static int is_dcf_jpg(const char* p){int n=slen(p);if(n<4)return 0;if(!(lc(p[n-4])=='.'&&lc(p[n-3])=='j'&&lc(p[n-2])=='p'&&lc(p[n-1])=='g'))return 0;for(int i=0;p[i];i++)if(p[i]=='D'&&p[i+1]=='S'&&p[i+2]=='C')return 1;return 0;}
static void bhex(char* o,unsigned long v){const char* H="0123456789abcdef";char t[16];int j=0;if(v==0)t[j++]='0';while(v){t[j++]=H[v&0xf];v>>=4;}int k=0;for(int i=j-1;i>=0;i--)o[k++]=t[i];o[k]=0;}
static void bdec(char* o,unsigned long v){char t[16];int j=0;if(v==0)t[j++]='0';while(v){t[j++]=(char)('0'+(int)(v%10));v/=10;}int k=0;for(int i=j-1;i>=0;i--)o[k++]=t[i];o[k]=0;}
static void logmsg(const char* m,int n){int fd=(int)sc(SYS_openx,(long)"/setting/grain_hook_4c.log",0x441,0666);if(fd<0)return;if(n<0)n=slen(m);sc(SYS_writex,fd,(long)m,n);sc(SYS_closex,fd,0,0);}
static void logskip(const char* why){ char b[96]; int k=0; const char* p="4c: SKIP "; while(*p)b[k++]=*p++; for(int i=0;why[i]&&k<90;i++)b[k++]=why[i]; b[k++]='\n'; logmsg(b,k); }
static long now_us(void){unsigned long tv[2]={0,0};sc(SYS_gettimeofday,(long)tv,0,0);return (long)tv[0]*1000000L+(long)tv[1];}
static void log_mem(void){ unsigned long si[32]; for(int i=0;i<32;i++)si[i]=0; sc(SYS_sysinfo,(long)si,0,0);
    char b[96]; int k=0; char t[16]; const char* p="4c: mem total=0x"; while(*p)b[k++]=*p++; bhex(t,si[4]); for(int i=0;t[i];i++)b[k++]=t[i];
    const char* q=" free=0x"; while(*q)b[k++]=*q++; bhex(t,si[5]); for(int i=0;t[i];i++)b[k++]=t[i]; b[k++]='\n'; logmsg(b,k); }

typedef long (*p_open)(long,long,long); typedef long (*p_close)(long); typedef long (*p_rw)(long,long,long);
typedef long (*p_remove)(long);
static p_open f_open; static p_close f_close; static p_rw f_read,f_write; static p_remove f_remove;
static int g_tried;
long Fsys_Open(long,long,long); long Fsys_Close(long h); long Fsys_Write(long,long,long);
static void* dl(const char* lib,const char* sym){void* h=__dlopen(lib,1);return h?__dlsym(h,sym):(void*)0;}
static void ensure(void){
    if(g_tried)return; g_tried=1;
    f_open=(p_open)dl("libInfraFsys.so","Fsys_Open");  f_close=(p_close)dl("libInfraFsys.so","Fsys_Close");
    f_read=(p_rw)dl("libInfraFsys.so","Fsys_Read");    f_write=(p_rw)dl("libInfraFsys.so","Fsys_Write");
    f_remove=(p_remove)dl("libInfraFsys.so","Fsys_Remove");
    if((void*)f_open==(void*)&Fsys_Open) f_open=0;  if((void*)f_close==(void*)&Fsys_Close) f_close=0;
    logmsg(f_close? "4c: Fsys resolved\n":"4c: Fsys resolve FAIL\n",-1);
}

#define NS 32
#define PL 128
static struct{long h;char used,written;char path[PL];} tab[NS];
static char done_ring[8][PL]; static int done_i;
static void t_open(long h,const char* p){int f=-1;for(int i=0;i<NS;i++){if(tab[i].used&&tab[i].h==h){f=i;break;}if(f<0&&!tab[i].used)f=i;}if(f<0)f=0;tab[f].h=h;tab[f].used=1;tab[f].written=0;int n=slen(p);if(n>=PL)n=PL-1;for(int i=0;i<n;i++)tab[f].path[i]=p[i];tab[f].path[n]=0;}
static void t_write(long h){for(int i=0;i<NS;i++)if(tab[i].used&&tab[i].h==h){tab[i].written=1;return;}}
static int t_take(long h,char* out){for(int i=0;i<NS;i++)if(tab[i].used&&tab[i].h==h){int w=tab[i].written;int n=0;while(tab[i].path[n]){out[n]=tab[i].path[n];n++;}out[n]=0;tab[i].used=0;return w;}return -1;}
static int recently_done(const char* p){for(int i=0;i<8;i++){int k=0,eq=1;while(done_ring[i][k]||p[k]){if(done_ring[i][k]!=p[k]){eq=0;break;}k++;}if(eq&&done_ring[i][0])return 1;}return 0;}
static void mark_done(const char* p){int n=slen(p);if(n>=PL)n=PL-1;for(int i=0;i<n;i++)done_ring[done_i][i]=p[i];done_ring[done_i][n]=0;done_i=(done_i+1)&7;}

static long find_seg(const unsigned char*b,long n,int want,long*seglen){
    long i=2; while(i+4<=n){ if(b[i]!=0xFF){i++;continue;} int mk=b[i+1];
        if(mk==0xD8||mk==0xD9||(mk>=0xD0&&mk<=0xD7)||mk==0x01){i+=2;continue;}
        if(mk==0xDA)break; int L=(b[i+2]<<8)|b[i+3]; long tot=2+L;
        if(mk==(want&0xFF)){*seglen=tot;return i;} i+=tot; } return -1; }
static int wrh(long h,const void*p,long n){ long w=0; while(w<n){ long r=f_write(h,(long)((const char*)p+w),n-w); if(r<=0)return 0; w+=r; } return 1; }

/* ---- codec I/O callbacks: read source from file, write encoded JPEG into a RAM buffer (Exif spliced) ---- */
typedef struct { long h; } rdctx_t;
static long read_cb(void* ctx, unsigned char* buf, unsigned long len){ rdctx_t* r=ctx; return f_read(r->h,(long)buf,(long)len); }
typedef struct { unsigned char* buf; unsigned long pos,cap; int spliced; const unsigned char* app1; long app1len; } wrctx_t;
static int putb(wrctx_t* w,const unsigned char* p,long n){ if(w->pos+(unsigned long)n>w->cap) return 0; for(long i=0;i<n;i++) w->buf[w->pos++]=p[i]; return 1; }
static long write_cb(void* ctx, const unsigned char* buf, unsigned long len){
    wrctx_t* w=ctx;
    if(!w->spliced){ w->spliced=1;
        if(w->app1len>0){ long a0len=0,a0=find_seg(buf,(long)len,0xE0,&a0len);
            if(a0>=0){ long ins=a0+a0len;
                if(!putb(w,buf,ins)||!putb(w,w->app1,w->app1len)||!putb(w,buf+ins,(long)len-ins)) return -1;
                return (long)len; } } }
    if(!putb(w,buf,(long)len)) return -1; return (long)len;
}

#define READ_FLAGS  0x01
#define WRITE_FLAGS 0x07
#define HEAD_CAP  (72UL*1024)
#define DEC_SCRATCH (256UL*1024)     /* covers chroma-passthrough scratch (4:2:2 ~137KB) */
#define ENC_CAP (8UL*1024*1024)      /* RAM grained-JPEG buffer */
#define ENC_SCRATCH (16UL*1024)     /* new swjpeg callback encoder needs ~10.5KB */
static char g_encarena[ENC_SCRATCH];
static long g_gstate[600];

static void roundtrip(const char* path){
    if(!f_open||!f_read||!f_write||!f_close||!f_remove){ logskip("resolve"); return; }
    void *head=0,*dscr=0,*enc=0; long rh=0,hh=0; int ok=0; const char* why="?";
    jpeg_image meta; jpeg_sdec dec; jpeg_senc se; rdctx_t rc; wrctx_t wc;
    /* 1. read the source head to grab Exif APP1 */
    head=xmmap(HEAD_CAP); if(!head){ why="mmap-head"; goto done; }
    if(f_open((long)path,(long)&hh,READ_FLAGS)<0||!hh){ hh=0; why="open-head"; goto done; }
    { unsigned long g=0; for(;;){ long r=f_read(hh,(long)((char*)head+g),4096); if(r<=0)break; g+=r; if(g>=HEAD_CAP)break; }
      f_close(hh); hh=0;
      long a1len=0,a1=find_seg((unsigned char*)head,(long)g,0xE1,&a1len);
      if(a1>=0 && a1+a1len<=(long)g){ wc.app1=(unsigned char*)head+a1; wc.app1len=a1len; } else { wc.app1=0; wc.app1len=0; } }
    log_mem();
    long t0=now_us();
    /* 2. callback-decode the source from the file + grain + encode into RAM (original untouched) */
    if(f_open((long)path,(long)&rh,READ_FLAGS)<0||!rh){ rh=0; why="open-rd"; goto done; }
    rc.h=rh;
    dscr=xmmap(DEC_SCRATCH); if(!dscr){ why="mmap-dec"; goto done; }
    if(jpeg_sdec_init_cb_ex(read_cb,&rc,dscr,DEC_SCRATCH,JPEG_COEF_CHROMA,&dec,&meta)!=0){ why="sdec-init"; goto done; }
    jpeg_sdec_set_xform(&dec,JPEG_XFORM_FAST);          /* AAN + chroma passthrough = ~2x codec */
    { char b[80]; int k=0; char t[16]; const char* p="4c: RT W="; while(*p)b[k++]=*p++; bdec(t,(unsigned long)meta.width); for(int i=0;t[i];i++)b[k++]=t[i]; const char* q=" H="; while(*q)b[k++]=*q++; bdec(t,(unsigned long)meta.height); for(int i=0;t[i];i++)b[k++]=t[i]; b[k++]='\n'; logmsg(b,k); }
    enc=xmmap(ENC_CAP); if(!enc){ why="mmap-enc"; goto done; }
    wc.buf=(unsigned char*)enc; wc.pos=0; wc.cap=ENC_CAP; wc.spliced=0;
    if(jpeg_senc_init_cb(write_cb,&wc,&meta,g_encarena,sizeof(g_encarena),&se)!=0){ why="senc-init"; goto done; }
    jpeg_senc_set_xform(&se,JPEG_XFORM_FAST);
    grain_stream_init(g_gstate,&meta,(unsigned)now_us(),0,0);
    long t1=now_us();
    { jpeg_comp bands[3]; int rows;
      for(;;){ rows=jpeg_sdec_band(&dec,bands); if(rows<0){ why="dec-band"; goto done; } if(rows==0) break;
          grain_stream_band(g_gstate,bands);
          if(jpeg_senc_band(&se,bands)!=0){ why="enc-band"; goto done; } } }
    { unsigned long el=0; if(jpeg_senc_fini(&se,&el)!=0){ why="senc-fini"; goto done; } }
    f_close(rh); rh=0;
    long t2=now_us();
    if(wc.pos<1000 || ((unsigned char*)enc)[0]!=0xFF || ((unsigned char*)enc)[1]!=0xD8){ why="encout"; goto done; }
    /* 3. land in one write (no .TMP): remove + create(0x7) + write the grained bytes over the original */
    f_remove((long)path);
    { long ph=0; if(f_open((long)path,(long)&ph,WRITE_FLAGS)<0||!ph){ why="create"; goto done; }
      int good=wrh(ph,enc,(long)wc.pos); f_close(ph);
      if(!good){ why="write-final"; goto done; } }
    long t3=now_us();
    ok=1;
    { char b[200]; int k=0; char t[16]; const char* p="4c: GRAIN ok bytes=0x"; while(*p)b[k++]=*p++; bhex(t,wc.pos); for(int i=0;t[i];i++)b[k++]=t[i];
      const char* q=" codec_us=0x"; while(*q)b[k++]=*q++; bhex(t,(unsigned long)(t2-t1)); for(int i=0;t[i];i++)b[k++]=t[i];
      const char* r=" land_us=0x"; while(*r)b[k++]=*r++; bhex(t,(unsigned long)(t3-t2)); for(int i=0;t[i];i++)b[k++]=t[i];
      const char* s=" total_us=0x"; while(*s)b[k++]=*s++; bhex(t,(unsigned long)(t3-t0)); for(int i=0;t[i];i++)b[k++]=t[i]; b[k++]='\n'; logmsg(b,k); }
done:
    if(hh&&f_close) f_close(hh);
    if(rh&&f_close) f_close(rh);
    xmunmap(head,HEAD_CAP); xmunmap(dscr,DEC_SCRATCH); xmunmap(enc,ENC_CAP);
    if(!ok) logskip(why);
}

long Fsys_Open(long a0,long a1,long a2){ ensure(); if(!f_open) return -1; long r=f_open(a0,a1,a2); if(r>=0 && a1 && is_dcf_jpg((const char*)a0)) t_open(*(long*)a1,(const char*)a0); return r; }
long Fsys_Write(long h,long b,long l){ ensure(); if(!f_write) return -1; long r=f_write(h,b,l); if(r>0) t_write(h); return r; }
long Fsys_Close(long h){ ensure(); if(!f_close) return -1; long r=f_close(h); char path[PL]; int w=t_take(h,path); if(w==1 && is_dcf_jpg(path) && !recently_done(path)){ mark_done(path); roundtrip(path); } return r; }
__attribute__((constructor)) static void init4c(void){ logmsg("4c: hook loaded\n",-1); }

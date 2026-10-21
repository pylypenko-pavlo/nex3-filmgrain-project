/* grain_hook_4b.c — Stage 4b: decode -> (NO grain) -> re-encode -> atomic writeback ROUNDTRIP.
 * Proves the full chain + measures codec time. NO pixel change yet. 4c adds the grain.
 *
 * FAIL-SAFE (absolute): the real Fsys_Close is called FIRST and its value returned UNCHANGED; the
 * roundtrip runs AFTER, reads the finished file, and writes the re-encoded JPEG to a TEMP path then
 * atomically renames over the original. ANY failure at ANY step -> original file UNTOUCHED, temp
 * removed, all mmaps freed. The close is never broken; the file is never partially overwritten.
 *
 * Build: arm-linux-gnueabi-gcc -march=armv5te -shared -fPIC -nostdlib -o grain_hook_4b.so grain_hook_4b.c
 * Resolution: __dlopen("<lib>.so",1)+__dlsym (RTLD_NEXT is dead on camera sonyld — Stage 4a finding).
 *
 * RE-RESOLVED 2026-10-20 (static disasm, stage4b-design.txt):
 *  - Fsys_Open flag encoding (@0x14452): bit0=READ, bit1=WRITE, bit4=TRUNC, bit5=CREATE.
 *    READ_FLAGS=0x01, WRITE_FLAGS=WRITE|CREATE|TRUNC=0x32 [INFERRED]. This hook ALSO logs the firmware's
 *    own open flags for DCF-JPGs ("4b: OPEN f=..") so the first boot test captures the ground-truth values.
 *  - codec Mcmd argv parsers: addr/size = BARE hex ("60000000"); a leading "0x" makes the parser stop at
 *    'x' and return 0. Dimensions = BARE decimal ("4912"). SetEncodeSetDst order =
 *    dstSizeX(dec),dstSizeY(dec),dstTgtSize(hex),dstBufVA(hex),dstBufSize(hex).
 *  - Decode/EncodeStillOnMemory handlers BOTH return 1 ALWAYS -> success+size are detected ONLY by
 *    validating the output JPEG (SOI 0xFFD8 + scan for EOI 0xFFD9), never by the return value.
 *  - decoder output format (4:2:2 vs 4:2:0) NOT pinned -> dst=W*H*2 is a safe over-allocation for 4b.
 */

/* ---------- raw syscalls ---------- */
static long sc(long n,long a,long b,long c){register long r7 __asm__("r7")=n,r0 __asm__("r0")=a,r1 __asm__("r1")=b,r2 __asm__("r2")=c;__asm__ volatile("svc #0":"+r"(r0):"r"(r7),"r"(r1),"r"(r2):"memory");return r0;}
static long sc6(long n,long a,long b,long c,long d,long e,long f){register long r7 __asm__("r7")=n,r0 __asm__("r0")=a,r1 __asm__("r1")=b,r2 __asm__("r2")=c,r3 __asm__("r3")=d,r4 __asm__("r4")=e,r5 __asm__("r5")=f;__asm__ volatile("svc #0":"+r"(r0):"r"(r7),"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5):"memory");return r0;}
#define SYS_write 4
#define SYS_open  5
#define SYS_close 6
#define SYS_gettimeofday 78
#define SYS_mmap2 192
#define SYS_munmap 91
#define PROT_RW 3
#define MAP_ANON_PRIV 0x22
/* mmap returns a page-aligned address; a HIGH address (e.g. 0xf7xxxxxx) is negative as a signed long,
 * so test UNSIGNED. Only the error range [-4095,-1] == [0xfffff001,0xffffffff] is a failure. */
static void* xmmap(unsigned long len){ unsigned long r=(unsigned long)sc6(SYS_mmap2,0,len,PROT_RW,MAP_ANON_PRIV,-1,0); return (r<0xfffff000UL)?(void*)r:(void*)0; }
static void  xmunmap(void* p,unsigned long len){ if(p&&len) sc(SYS_munmap,(long)p,len,0); }

/* ---------- sonyld resolve ---------- */
extern void* __dlopen(const char* p,int m);
extern void* __dlsym(void* h,const char* n);

/* ---------- tiny helpers ---------- */
static int slen(const char* s){int n=0;if(!s)return 0;while(s[n])n++;return n;}
static char lc(char c){return (c>='A'&&c<='Z')?(char)(c+32):c;}
static int is_dcf_jpg(const char* p){int n=slen(p);if(n<4)return 0;if(!(lc(p[n-4])=='.'&&lc(p[n-3])=='j'&&lc(p[n-2])=='p'&&lc(p[n-1])=='g'))return 0;for(int i=0;p[i];i++)if(p[i]=='D'&&p[i+1]=='S'&&p[i+2]=='C')return 1;return 0;}
/* BARE hex (no "0x") and BARE decimal — matches the two Mcmd argv parsers */
static void bhex(char* o,unsigned long v){const char* H="0123456789abcdef";char t[16];int j=0;if(v==0)t[j++]='0';while(v){t[j++]=H[v&0xf];v>>=4;}int k=0;for(int i=j-1;i>=0;i--)o[k++]=t[i];o[k]=0;}
static void bdec(char* o,unsigned long v){char t[16];int j=0;if(v==0)t[j++]='0';while(v){t[j++]=(char)('0'+(int)(v%10));v/=10;}int k=0;for(int i=j-1;i>=0;i--)o[k++]=t[i];o[k]=0;}
static void logmsg(const char* m,int n){int fd=(int)sc(SYS_open,(long)"/setting/grain_hook_4b.log",0x441,0666);if(fd<0)return;if(n<0)n=slen(m);sc(SYS_write,fd,(long)m,n);sc(SYS_close,fd,0,0);}
static void logskip(const char* why){ char b[96]; int k=0; const char* p="4b: SKIP "; while(*p)b[k++]=*p++; for(int i=0;why[i]&&k<90;i++)b[k++]=why[i]; b[k++]='\n'; logmsg(b,k); }
static long now_us(void){unsigned long tv[2]={0,0};sc(SYS_gettimeofday,(long)tv,0,0);return (long)tv[0]*1000000L+(long)tv[1];}

/* ---------- resolved Fsys + codec pointers ---------- */
typedef long (*p_open)(long,long,long);          /* Fsys_Open(path,outHandle*,flags) */
typedef long (*p_close)(long);                    /* Fsys_Close(handle) */
typedef long (*p_rw)(long,long,long);             /* Fsys_Read/Write(handle,buf,len) */
typedef long (*p_rename)(long,long);              /* Fsys_Rename(old,new) */
typedef long (*p_remove)(long);                   /* Fsys_Remove(path) */
typedef long (*p_mcmd)(long,char**);              /* MprIfMcmd handlers: (argc,argv) */
static p_open  f_open;  static p_close f_close; static p_rw f_read, f_write;
static p_rename f_rename; static p_remove f_remove;
static p_mcmd m_dec_src,m_dec_dst,m_dec_disp,m_decode, m_enc_src,m_enc_dst,m_encode;
static int g_tried;
long Fsys_Open(long a0,long a1,long a2);  long Fsys_Close(long h);  long Fsys_Write(long h,long b,long l);
static void* dl(const char* lib,const char* sym){void* h=__dlopen(lib,1);return h?__dlsym(h,sym):(void*)0;}
static void ensure(void){
    if(g_tried)return; g_tried=1;
    f_open=(p_open)dl("libInfraFsys.so","Fsys_Open");  f_close=(p_close)dl("libInfraFsys.so","Fsys_Close");
    f_read=(p_rw)dl("libInfraFsys.so","Fsys_Read");    f_write=(p_rw)dl("libInfraFsys.so","Fsys_Write");
    f_rename=(p_rename)dl("libInfraFsys.so","Fsys_Rename"); f_remove=(p_remove)dl("libInfraFsys.so","Fsys_Remove");
    if((void*)f_open==(void*)&Fsys_Open) f_open=0;  if((void*)f_close==(void*)&Fsys_Close) f_close=0;
    m_dec_src=(p_mcmd)dl("libmpr.so","_ZN9MprIfMcmd28SetDecodeStillOnMemorySetSrcElPPc");
    m_dec_dst=(p_mcmd)dl("libmpr.so","_ZN9MprIfMcmd28SetDecodeStillOnMemorySetDstElPPc");
    m_dec_disp=(p_mcmd)dl("libmpr.so","_ZN9MprIfMcmd31SetDecodeStillOnMemoryDispParamElPPc");
    m_decode=(p_mcmd)dl("libmpr.so","_ZN9MprIfMcmd19DecodeStillOnMemoryElPPc");
    m_enc_src=(p_mcmd)dl("libmpr.so","_ZN9MprIfMcmd28SetEncodeStillOnMemorySetSrcElPPc");
    m_enc_dst=(p_mcmd)dl("libmpr.so","_ZN9MprIfMcmd28SetEncodeStillOnMemorySetDstElPPc");
    m_encode=(p_mcmd)dl("libmpr.so","_ZN9MprIfMcmd19EncodeStillOnMemoryElPPc");
    logmsg(f_close? "4b: Fsys resolved\n":"4b: Fsys resolve FAIL\n",-1);
    logmsg(m_decode&&m_encode? "4b: codec resolved\n":"4b: codec resolve FAIL\n",-1);
}

/* ---------- handle tracking + idempotency ---------- */
#define NS 32
#define PL 128
static struct{long h;char used,written;char path[PL];} tab[NS];
static char done_ring[8][PL]; static int done_i;
static void t_open(long h,const char* p){int f=-1;for(int i=0;i<NS;i++){if(tab[i].used&&tab[i].h==h){f=i;break;}if(f<0&&!tab[i].used)f=i;}if(f<0)f=0;tab[f].h=h;tab[f].used=1;tab[f].written=0;int n=slen(p);if(n>=PL)n=PL-1;for(int i=0;i<n;i++)tab[f].path[i]=p[i];tab[f].path[n]=0;}
static void t_write(long h){for(int i=0;i<NS;i++)if(tab[i].used&&tab[i].h==h){tab[i].written=1;return;}}
static int t_take(long h,char* out){for(int i=0;i<NS;i++)if(tab[i].used&&tab[i].h==h){int w=tab[i].written;int n=0;while(tab[i].path[n]){out[n]=tab[i].path[n];n++;}out[n]=0;tab[i].used=0;return w;}return -1;}
static int recently_done(const char* p){for(int i=0;i<8;i++){int k=0,eq=1;while(done_ring[i][k]||p[k]){if(done_ring[i][k]!=p[k]){eq=0;break;}k++;}if(eq&&done_ring[i][0])return 1;}return 0;}
static void mark_done(const char* p){int n=slen(p);if(n>=PL)n=PL-1;for(int i=0;i<n;i++)done_ring[done_i][i]=p[i];done_ring[done_i][n]=0;done_i=(done_i+1)&7;}

/* ---------- SOF0 parse: scan JPEG markers for frame W,H ---------- */
static int parse_wh(const unsigned char* d,unsigned long n,int* W,int* H){
    if(n<4||d[0]!=0xFF||d[1]!=0xD8)return 0;      /* SOI */
    unsigned long i=2;
    while(i+4<n){
        if(d[i]!=0xFF){i++;continue;}
        unsigned char m=d[i+1];
        if(m==0xD8||m==0xD9||(m>=0xD0&&m<=0xD7)||m==0x01){i+=2;continue;}
        unsigned seglen=(d[i+2]<<8)|d[i+3];
        if(m>=0xC0&&m<=0xCF&&m!=0xC4&&m!=0xC8&&m!=0xCC){   /* SOFn */
            if(i+9>=n)return 0;
            *H=(d[i+5]<<8)|d[i+6]; *W=(d[i+7]<<8)|d[i+8];
            return (*W>0&&*H>0&&*W<=8192&&*H<=8192);
        }
        i+=2+seglen;
    }
    return 0;
}

/* ---------- build a numeric argv per a format spec and run an Mcmd subcommand ----------
 * fmt chars: 'h' = bare hex arg, 'd' = bare decimal arg (one char per value, up to 5).
 * argv[0] is an ignored command-name slot; argc = (#values)+1 so the handler's argc>N guard passes. */
static long callm(p_mcmd fn,const char* fmt,unsigned long a0,unsigned long a1,unsigned long a2,unsigned long a3,unsigned long a4){
    if(!fn) return -1;
    unsigned long v[5]={a0,a1,a2,a3,a4};
    char d0[2]={'x',0}; char bb[5][24]; char* argv[7];
    argv[0]=d0; int cnt=0;
    for(int i=0;fmt[i]&&i<5;i++){ if(fmt[i]=='h') bhex(bb[i],v[i]); else bdec(bb[i],v[i]); argv[1+i]=bb[i]; cnt++; }
    argv[1+cnt]=0;
    return fn(cnt+1,argv);   /* return is ALWAYS 1 for decode/encode handlers -> ignored by caller */
}

/* ---------- the roundtrip (runs AFTER the real close; original untouched on any failure) ---------- */
#define READ_FLAGS  0x01            /* Fsys READ (bit0)                         [INFERRED+logged] */
#define WRITE_FLAGS 0x32            /* Fsys WRITE|CREATE|TRUNC (bit1|bit5|bit4)  [INFERRED+logged] */
#define SRC_CAP (16UL*1024*1024)
#define ENC_CAP (16UL*1024*1024)
static void roundtrip(const char* path){
    if(!f_open||!f_read||!f_write||!f_close||!f_rename||!m_dec_src||!m_dec_dst||!m_decode||!m_enc_src||!m_enc_dst||!m_encode){ logskip("resolve"); return; }
    void* src=0; void* pix=0; void* enc=0; long rh=0, th=0; int ok=0;
    int W=0,Hh=0; unsigned long pixsz=0; const char* why="?";
    /* temp path: same name, ".TMP" */
    char tmp[PL]; int n=slen(path); if(n<5||n>=PL-1){ logskip("path"); return; }
    for(int i=0;i<n;i++)tmp[i]=path[i]; tmp[n-3]='T';tmp[n-2]='M';tmp[n-1]='P';tmp[n]=0;
    src=xmmap(SRC_CAP); if(!src){ why="mmap-src"; goto done; }
    /* 1. read the whole JPEG */
    if(f_open((long)path,(long)&rh,READ_FLAGS)<0||!rh){ rh=0; why="open-rd"; goto done; }
    unsigned long got=0; for(;;){ long r=f_read(rh,(long)((char*)src+got),4096); if(r<=0)break; got+=r; if(got>=SRC_CAP){ got=0; break; } }
    f_close(rh); rh=0;
    if(got<100){ why="short-read"; goto done; }
    if(!parse_wh((unsigned char*)src,got,&W,&Hh)){ why="sof-parse"; goto done; }
    pixsz=(unsigned long)W*(unsigned long)Hh*2;     /* 4:2:2 safe over-alloc (fits 4:2:0 too) */
    { char b[96]; int k=0; const char* p="4b: RT got=0x"; while(*p)b[k++]=*p++; char t[24]; bhex(t,got); for(int i=0;t[i];i++)b[k++]=t[i]; const char* q=" W="; while(*q)b[k++]=*q++; bdec(t,(unsigned long)W); for(int i=0;t[i];i++)b[k++]=t[i]; const char* r=" H="; while(*r)b[k++]=*r++; bdec(t,(unsigned long)Hh); for(int i=0;t[i];i++)b[k++]=t[i]; b[k++]='\n'; logmsg(b,k); }
    pix=xmmap(pixsz); enc=xmmap(ENC_CAP); if(!pix||!enc){ why="mmap-pix/enc"; goto done; }
    /* 2. DECODE (timed): SetSrc(srcVA,srcSize,W,H) + SetDst(dstVA,maxDstSize,0,0); DispParam SKIPPED (optional).
     *    Both handler returns are ALWAYS 1 -> ignored; decode validated via the final encode output. */
    long t0=now_us();
    callm(m_dec_src,"hhdd",(unsigned long)src,got,(unsigned long)W,(unsigned long)Hh,0);
    callm(m_dec_dst,"hhdd",(unsigned long)pix,pixsz,0,0,0);
    { char* av[2]={(char*)"x",0}; m_decode(1,av); }          /* execute decode (return ignored) */
    long t1=now_us();
    /* 3. (4b: NO pixel change) */
    /* 4. ENCODE (timed): SetSrc(pixVA,W,H) + SetDst(dstSizeX,dstSizeY,dstTgtSize,dstBufVA,dstBufSize). */
    callm(m_enc_src,"hdd",(unsigned long)pix,(unsigned long)W,(unsigned long)Hh,0,0);
    callm(m_enc_dst,"ddhhh",(unsigned long)W,(unsigned long)Hh,ENC_CAP,(unsigned long)enc,ENC_CAP);
    { char* av[2]={(char*)"x",0}; m_encode(1,av); }          /* execute encode (return ignored) */
    long t2=now_us();
    /* 5. validate output: SOI + scan for EOI to get byte count (handler return is not the size) */
    unsigned char* e=(unsigned char*)enc;
    if(e[0]!=0xFF||e[1]!=0xD8){ why="no-SOI"; goto done; }
    long enc_sz=0;
    for(unsigned long i=2;i+1<ENC_CAP;i++){ if(e[i]==0xFF&&e[i+1]==0xD9){ enc_sz=(long)i+2; break; } }
    if(enc_sz<1000||(unsigned long)enc_sz>ENC_CAP){ why="no-EOI/size"; goto done; }
    /* 6. write temp, then atomic rename over the original */
    if(f_open((long)tmp,(long)&th,WRITE_FLAGS)<0||!th){ th=0; why="open-wr"; goto done; }
    { unsigned long w=0; while(w<(unsigned long)enc_sz){ long r=f_write(th,(long)((char*)enc+w),enc_sz-w); if(r<=0)break; w+=r; } f_close(th); th=0; if(w!=(unsigned long)enc_sz){ if(f_remove)f_remove((long)tmp); why="short-write"; goto done; } }
    if(f_rename((long)tmp,(long)path)<0){ if(f_remove)f_remove((long)tmp); why="rename"; goto done; }
    ok=1;
    { char b[160]; int k=0; char t[24]; const char* p="4b: ROUNDTRIP ok dec_us=0x"; while(*p)b[k++]=*p++; bhex(t,(unsigned long)(t1-t0)); for(int i=0;t[i];i++)b[k++]=t[i]; const char* q=" enc_us=0x"; while(*q)b[k++]=*q++; bhex(t,(unsigned long)(t2-t1)); for(int i=0;t[i];i++)b[k++]=t[i]; const char* r=" bytes=0x"; while(*r)b[k++]=*r++; bhex(t,(unsigned long)enc_sz); for(int i=0;t[i];i++)b[k++]=t[i]; b[k++]='\n'; logmsg(b,k); }
done:
    if(rh&&f_close) f_close(rh);
    if(th&&f_close){ f_close(th); if(f_remove)f_remove((long)tmp); }
    xmunmap(src,SRC_CAP); xmunmap(pix,pixsz); xmunmap(enc,ENC_CAP);
    if(!ok) logskip(why);
}

/* ---------- interposers ---------- */
long Fsys_Open(long a0,long a1,long a2){
    ensure(); if(!f_open) return -1;
    long r=f_open(a0,a1,a2);
    if(r>=0 && a1 && is_dcf_jpg((const char*)a0)){
        t_open(*(long*)a1,(const char*)a0);
        /* ground-truth capture of the firmware's own open flags (confirms READ/WRITE_FLAGS) */
        char b[160]; int k=0; char t[24]; const char* p="4b: OPEN f=0x"; while(*p)b[k++]=*p++; bhex(t,(unsigned long)a2); for(int i=0;t[i];i++)b[k++]=t[i]; b[k++]=' '; const char* s=(const char*)a0; for(int i=0;s[i]&&k<150;i++)b[k++]=s[i]; b[k++]='\n'; logmsg(b,k);
    }
    return r;
}
long Fsys_Write(long h,long b,long l){
    ensure(); if(!f_write) return -1;
    long r=f_write(h,b,l);
    if(r>0) t_write(h);
    return r;
}
long Fsys_Close(long h){
    ensure(); if(!f_close) return -1;
    long r=f_close(h);                      /* real close FIRST, value returned UNCHANGED */
    char path[PL]; int w=t_take(h,path);
    if(w==1 && is_dcf_jpg(path) && !recently_done(path)){ mark_done(path); roundtrip(path); }
    return r;
}
__attribute__((constructor)) static void init4b(void){ logmsg("4b: hook loaded\n",-1); }

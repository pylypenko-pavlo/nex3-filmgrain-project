/* Offline codec-path test: isolates the FAST + chroma-passthrough roundtrip from the Fsys/dlsym shim.
 * Reads a fixture JPEG into RAM, runs jpeg_sdec_init_cb_ex(CHROMA passthrough)+FAST -> grain_stream_band
 * -> jpeg_senc_init_cb+FAST, and PRINTS every return code (esp. senc_init) + the first band's coef flags.
 * Writes the grained JPEG to argv[2]. Hosted build (libc for printf/malloc/fopen); swjpeg's memcpy/memset
 * are static so they coexist. Build from this directory (grain_tile.bin must be in cwd for the .incbin). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include "swjpeg.h"

extern void grain_stream_init(void*, const jpeg_image*, unsigned, short*, unsigned long);
extern int  grain_stream_band(void*, jpeg_comp[3]);

static unsigned char *g_src; static unsigned long g_srclen, g_srcpos;
static long read_cb(void *ctx, unsigned char *buf, unsigned long len){
    (void)ctx; unsigned long n = g_srclen - g_srcpos; if(n>len) n=len; if(!n) return 0;
    memcpy(buf, g_src+g_srcpos, n); g_srcpos += n; return (long)n;
}
static unsigned char *g_out; static unsigned long g_outpos, g_outcap;
static long write_cb(void *ctx, const unsigned char *buf, unsigned long len){
    (void)ctx; if(g_outpos+len > g_outcap) return -1; memcpy(g_out+g_outpos, buf, len); g_outpos += len; return (long)len;
}
static long g_gstate[600];
static long us(void){ struct timeval t; gettimeofday(&t,0); return (long)t.tv_sec*1000000L + t.tv_usec; }

int main(int argc, char **argv){
    if(argc<3){ fprintf(stderr,"usage: %s in.jpg out.jpg [fast|accurate]\n",argv[0]); return 9; }
    int fast = !(argc>3 && argv[3][0]=='a');          /* default fast; "accurate" => ACCURATE + no passthrough */
    unsigned opts = fast ? JPEG_COEF_CHROMA : 0u;      /* fast path keeps chroma as coef (passthrough) */
    int xm = fast ? JPEG_XFORM_FAST : JPEG_XFORM_ACCURATE;
    printf("MODE=%s opts=%u xform=%d\n", fast?"FAST+PT":"ACCURATE+full", opts, xm);
    FILE *f=fopen(argv[1],"rb"); if(!f){ perror("open in"); return 9; }
    fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET);
    g_src=malloc(sz); if(fread(g_src,1,sz,f)!=(size_t)sz){ return 9; } fclose(f);
    g_srclen=(unsigned long)sz; g_srcpos=0;

    static char dscr[256*1024];
    static char escr[16*1024];
    g_outcap=16UL*1024*1024; g_out=malloc(g_outcap); g_outpos=0;

    jpeg_image meta; jpeg_sdec dec; jpeg_senc se; int rc;

    rc = jpeg_sdec_init_cb_ex(read_cb, 0, dscr, sizeof dscr, opts, &dec, &meta);
    printf("sdec_init rc=%d  W=%d H=%d ncomp=%d hmax=%d vmax=%d ri=%d\n",
           rc, meta.width, meta.height, meta.ncomp, meta.hmax, meta.vmax, meta.restart_interval);
    if(rc){ printf("FAIL sdec_init\n"); return 1; }
    for(int i=0;i<meta.ncomp;i++)
        printf("  comp[%d] h=%d v=%d tq=%d  qt[tq][0..2]=%u,%u,%u\n", i,
               meta.comp[i].h, meta.comp[i].v, meta.comp[i].tq,
               meta.qt[meta.comp[i].tq][0], meta.qt[meta.comp[i].tq][1], meta.qt[meta.comp[i].tq][2]);
    jpeg_sdec_set_xform(&dec, xm);

    rc = jpeg_senc_init_cb(write_cb, 0, &meta, escr, sizeof escr, &se);
    printf("senc_init rc=%d   (scratch given=%lu)\n", rc, (unsigned long)sizeof escr);
    if(rc){ printf("FAIL senc_init rc=%d  [JPEG_ERR_ARG=%d ARENA=%d]\n", rc, JPEG_ERR_ARG, JPEG_ERR_ARENA); return 2; }
    jpeg_senc_set_xform(&se, xm);
    grain_stream_init(g_gstate, &meta, 12345u, 0, 0);

    jpeg_comp bands[3]; int rows, nb=0; long t0=us();
    while((rows=jpeg_sdec_band(&dec, bands))>0){
        if(nb==0) printf("  band0 coef: Y=%d Cb=%d Cr=%d  (grain runs where coef==0)\n",
                         bands[0].coef, bands[1].coef, bands[2].coef);
        grain_stream_band(g_gstate, bands);
        rc = jpeg_senc_band(&se, bands);
        if(rc){ printf("FAIL senc_band rc=%d at band %d\n", rc, nb); return 3; }
        nb++;
    }
    if(rows<0){ printf("FAIL sdec_band rc=%d\n", rows); return 4; }
    unsigned long outlen=0; rc=jpeg_senc_fini(&se,&outlen); long t1=us();
    printf("senc_fini rc=%d  bands=%d  codec_us=%ld  outbytes=%lu\n", rc, nb, t1-t0, g_outpos);
    if(rc){ printf("FAIL senc_fini\n"); return 5; }

    FILE *o=fopen(argv[2],"wb"); fwrite(g_out,1,g_outpos,o); fclose(o);
    printf("OK wrote %s\n", argv[2]);
    return 0;
}

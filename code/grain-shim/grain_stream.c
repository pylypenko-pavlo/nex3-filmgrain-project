/* grain_stream.c - BAKED-TILE film grain (ultramax400 retune). Per pixel: look up a pre-baked toroidal grain
 * tile (rodata, grain_tile.S) and multiply by the granularity LUT indexed by the CO-LOCATED luma. NO per-pixel
 * hash, NO runtime blur, NO ring scratch -> ~10x faster than the hash+blur version, same look. Y/Cb/Cr use
 * independent toroidal offsets (per-frame random). Freestanding, integer-only. */
#include "swjpeg.h"
#include "grain_luts.h"            /* GRAIN_TILE(512), GRAIN_TMASK(511), GAIN_Y/CB/CR[256] */
extern const signed char grain_tile[];
typedef unsigned int u32;
#define SHIFT 8
static u32 hashn(u32 x,u32 y,u32 s){ u32 u=x*0x9E3779B1u^y*0x85EBCA77u^s*0xC2B2AE3Du; u^=u>>15; u*=0x2C1B3C6Du; u^=u>>12; u*=0x297A2D39u; u^=u>>15; return u; }
static int clampi(int v,int lo,int hi){ return v<lo?lo:(v>hi?hi:v); }
static int idiv(int a,int b){ int q=0; if(b<=0) return 0; while(a>=b){a-=b;q++;} return q; }

typedef struct { int ox,oy; const short* GAIN; } gctx;
typedef struct { gctx c[3]; int ncomp,hmax,vmax; } grain_stream;

void grain_stream_init(grain_stream*g,const jpeg_image*meta,u32 seed,short*scratch,unsigned long slen){
    (void)scratch;(void)slen;
    g->ncomp=meta->ncomp; g->hmax=meta->hmax; g->vmax=meta->vmax;
    const short* GA[3]={GAIN_Y,GAIN_CB,GAIN_CR};
    for(int i=0;i<3;i++){ g->c[i].GAIN=GA[i];
        u32 h=hashn((u32)(i*2+1),0u,seed); g->c[i].ox=(int)(h&GRAIN_TMASK); g->c[i].oy=(int)((h>>12)&GRAIN_TMASK); }
}
static void grain_band_comp(grain_stream*g,int ci,jpeg_comp*comp,const jpeg_comp*Y){
    gctx*c=&g->c[ci];
    int rx=idiv(g->hmax,comp->h), ry=idiv(g->vmax,comp->v);
    for(int r=0;r<comp->height;r++){
        int absY=comp->y0+r;
        int ty=(((absY+c->oy)&GRAIN_TMASK))*GRAIN_TILE;
        int ly=clampi(absY*ry - Y->y0,0,Y->height-1);
        unsigned char*prow=comp->data+(long)r*comp->stride;
        const unsigned char*yrow=Y->data+(long)ly*Y->stride;
        for(int x=0;x<comp->width;x++){
            int ni=(int)grain_tile[ty + ((x+c->ox)&GRAIN_TMASK)];
            int lx=clampi(x*rx,0,Y->width-1);
            int gg=(ni*(int)c->GAIN[yrow[lx]])>>SHIFT;
            prow[x]=(unsigned char)clampi((int)prow[x]+gg,0,255);
        }
    }
}
int grain_stream_band(grain_stream*g,jpeg_comp bands[3]){
    if(!bands[0].coef) grain_band_comp(g,0,&bands[0],&bands[0]);   /* Y = pixels */
    if(g->ncomp>=3){                                               /* chroma: skip passthrough (coef) bands */
        if(!bands[1].coef) grain_band_comp(g,1,&bands[1],&bands[0]);
        if(!bands[2].coef) grain_band_comp(g,2,&bands[2],&bands[0]);
    }
    return 0;
}

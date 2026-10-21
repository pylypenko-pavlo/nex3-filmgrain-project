/* grain.c - freestanding integer film-grain pass (ultramax400/0.15 look) on decoded JPEG planes.
 * Matches the validated int_grain.py: per-pixel u32 hash noise -> separable blur K=[1,4,11,16,11,4,1]/48
 * (luma 1 separable pass; chroma 2 passes = coarser) -> plane' = clip(plane + (blur*GAIN[lumaY])>>8).
 * Chroma gain is indexed by the CO-LOCATED luma; Y/Cb/Cr use INDEPENDENT noise seeds (decorrelated).
 * GAIN_* LUTs are baked from int_grain.py (grain_luts.h). No libc / no float / integer only.
 * Full-plane scratch (two int16 planes >= pw*ph of the largest component). */
#include "swjpeg.h"
#include "grain_luts.h"
typedef unsigned int u32;
#define SHIFT 8
static const int K[7]={1,4,11,16,11,4,1};
#define KSUM 48

static u32 hashn(u32 x,u32 y,u32 s){
    u32 u=x*0x9E3779B1u ^ y*0x85EBCA77u ^ s*0xC2B2AE3Du;
    u^=u>>15; u*=0x2C1B3C6Du; u^=u>>12; u*=0x297A2D39u; u^=u>>15; return u;
}
static int clampi(int v,int lo,int hi){ return v<lo?lo:(v>hi?hi:v); }
static int floordiv48(int x){ int q=x/KSUM; if((x%KSUM)!=0 && x<0) q--; return q; }  /* /48 const -> mul+shift */
static int idiv(int a,int b){ int q=0; if(b<=0) return 0; while(a>=b){a-=b;q++;} return q; }  /* small +ve ratios only */

/* fill a[] with hash noise in [-128,127], then `passes` separable blur passes; result left in a[].
 * a,b are int16 planes of pw*ph (b is scratch). Edges use clamp (interior stats unchanged). */
static void noise_blur(short*a,short*b,int pw,int ph,u32 seed,int passes){
    for(int y=0;y<ph;y++){ int row=y*pw; for(int x=0;x<pw;x++) a[row+x]=(short)((int)(hashn((u32)x,(u32)y,seed)&0xFFu)-128); }
    for(int p=0;p<passes;p++){
        for(int y=0;y<ph;y++){ int row=y*pw;
            for(int x=0;x<pw;x++){ int acc=0;
                for(int j=0;j<7;j++) acc+=K[j]*a[row+clampi(x+j-3,0,pw-1)];
                b[row+x]=(short)floordiv48(acc+KSUM/2);
            }
        }
        for(int x=0;x<pw;x++){
            for(int y=0;y<ph;y++){ int acc=0;
                for(int j=0;j<7;j++) acc+=K[j]*b[clampi(y+j-3,0,ph-1)*pw+x];
                a[y*pw+x]=(short)floordiv48(acc+KSUM/2);
            }
        }
    }
}

/* apply grain to one component, gain indexed by the co-located luma (Y component = comp[0]). */
static void grain_comp(jpeg_image*im,int ci,const short*GAIN,u32 seed,short*a,short*b,int passes){
    jpeg_comp*c=&im->comp[ci];
    const jpeg_comp*Y=&im->comp[0];
    int rx=idiv(im->hmax,c->h), ry=idiv(im->vmax,c->v);   /* luma/chroma ratio, computed once (no per-pixel divide) */
    noise_blur(a,b,c->pw,c->ph,seed,passes);
    for(int y=0;y<c->height;y++){
        int ly=clampi(y*ry,0,Y->height-1);
        unsigned char*prow=c->data+(long)y*c->stride;
        const unsigned char*yrow=Y->data+(long)ly*Y->stride;
        const short*nrow=a+(long)y*c->pw;
        for(int x=0;x<c->width;x++){
            int lx=clampi(x*rx,0,Y->width-1);
            int g=((int)nrow[x]*(int)GAIN[yrow[lx]])>>SHIFT;
            prow[x]=(unsigned char)clampi((int)prow[x]+g,0,255);
        }
    }
}

/* scratch must be >= 2 * (pw*ph) shorts of the LARGEST component (== luma). seed = per-frame. */
int grain_apply(jpeg_image*im,u32 seed,short*scratch,unsigned long scratch_shorts){
    int pw=im->comp[0].pw, ph=im->comp[0].ph;
    unsigned long need=2UL*(unsigned long)pw*(unsigned long)ph;
    if(scratch_shorts<need) return -1;
    short*a=scratch, *b=scratch+(unsigned long)pw*ph;
    grain_comp(im,0,GAIN_Y, seed,     a,b,1);          /* luma: 1 blur pass */
    if(im->ncomp>=3){
        grain_comp(im,1,GAIN_CB,seed+101u,a,b,2);      /* chroma: 2 passes (coarser), independent seeds */
        grain_comp(im,2,GAIN_CR,seed+202u,a,b,2);
    }
    return 0;
}

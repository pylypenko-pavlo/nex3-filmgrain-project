/* test harness (libc, NOT shipped): in.jpg -> decode -> grain_apply -> encode -> out.jpg */
#include <stdio.h>
#include <stdlib.h>
#include "swjpeg.h"
int grain_apply(jpeg_image*,unsigned,short*,unsigned long);
int main(int argc,char**argv){
    if(argc<3){fprintf(stderr,"usage: %s in.jpg out.jpg [seed]\n",argv[0]);return 2;}
    FILE*f=fopen(argv[1],"rb"); if(!f){perror("open");return 1;}
    fseek(f,0,SEEK_END); long n=ftell(f); fseek(f,0,SEEK_SET);
    unsigned char*buf=malloc(n); if(fread(buf,1,n,f)!=(size_t)n){return 1;} fclose(f);
    unsigned long asz=jpeg_decode_arena_size(buf,n);
    if(!asz){fprintf(stderr,"arena_size fail\n");return 1;}
    void*arena=malloc(asz); jpeg_image im;
    int r=jpeg_decode(buf,n,arena,asz,&im);
    if(r){fprintf(stderr,"decode err %d\n",r);return 1;}
    printf("decoded %dx%d ncomp=%d  Y %dx%d(pw%d ph%d)  Cb %dx%d  hmax%d vmax%d\n",
        im.width,im.height,im.ncomp,im.comp[0].width,im.comp[0].height,im.comp[0].pw,im.comp[0].ph,
        im.comp[1].width,im.comp[1].height,im.hmax,im.vmax);
    unsigned seed=argc>3?(unsigned)atoi(argv[3]):7u;
    unsigned long ss=2UL*(unsigned long)im.comp[0].pw*(unsigned long)im.comp[0].ph;
    short*scr=malloc(ss*sizeof(short));
    if(grain_apply(&im,seed,scr,ss)){fprintf(stderr,"grain scratch err\n");return 1;}
    unsigned long esz=jpeg_encode_arena_size(); void*earena=malloc(esz);
    unsigned long outcap=(unsigned long)im.width*(unsigned long)im.height*2;
    unsigned char*out=malloc(outcap); unsigned long outlen=outcap;
    r=jpeg_encode(&im,earena,esz,out,&outlen);
    if(r){fprintf(stderr,"encode err %d\n",r);return 1;}
    FILE*o=fopen(argv[2],"wb"); fwrite(out,1,outlen,o); fclose(o);
    printf("wrote %s  %lu bytes (seed %u)\n",argv[2],outlen,seed);
    return 0;
}

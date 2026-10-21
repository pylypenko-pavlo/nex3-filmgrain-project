/*
 * swjpeg.h - freestanding, integer-only baseline JPEG codec (decoder + encoder)
 * for ARMv5TE, no libc, no libgcc, no floating point, no malloc, no syscalls.
 *
 * Build the codec TU with:
 *     arm-linux-gnueabi-gcc -march=armv5te -nostdlib -fPIC -c swjpeg.c
 *
 * The codec only needs unaligned-safe byte access; all word accesses are to
 * naturally aligned objects (the arena is aligned internally to 32 bytes).
 *
 * ------------------------------------------------------------------------
 * Memory model
 * ------------------------------------------------------------------------
 * jpeg_decode():   planes are allocated INSIDE the caller-provided arena.
 *                  jpeg_decode_arena_size() returns the exact arena size (it already
 *                  contains the 32-byte alignment slack). Measured for 4912x3264:
 *                      4:2:2 (the Sony NEX-3N SOOC frame): 32,080,064 bytes (30.59 MiB)
 *                          Y 16,032,768 + Cb 8,016,384 + Cr 8,016,384 + ~12 KB context
 *                      4:2:0: 24,063,680 bytes (22.95 MiB)
 *                      4:4:4: 48,112,832 bytes (45.88 MiB)
 *                  The decoded planes stay valid as long as the arena lives.
 * jpeg_encode():   needs jpeg_encode_arena_size() bytes (6,400 incl. slack) of scratch
 *                  and a caller-provided output buffer (see *outlen). Stack use of the
 *                  whole codec is < ~2 KB.
 * Streaming API:   see the section at the end of this file: scratch for 16 MP is ~0.1 MB.
 *
 * ------------------------------------------------------------------------
 * Plane geometry (decoder output == encoder input)
 * ------------------------------------------------------------------------
 *  - Samples are unsigned 8-bit, JFIF YCbCr (comp[0]=Y, comp[1]=Cb, comp[2]=Cr),
 *    NO colour conversion is done anywhere in the codec.
 *  - Each plane is padded to a whole number of MCUs:
 *        pw = mcus_x * h * 8,  ph = mcus_y * v * 8,   stride == pw
 *    The visible part is width x height (= ceil(W*h/hmax) x ceil(H*v/vmax)).
 *    The padding area holds real decoded data and is what the encoder re-encodes,
 *    so a plane that is only modified inside width x height stays consistent.
 *  - For a caller-built jpeg_image the encoder requires
 *        stride >= mcus_x*h*8   and   ph >= mcus_y*v*8.
 */
#ifndef SWJPEG_H
#define SWJPEG_H

#ifdef __cplusplus
extern "C" {
#endif

#define JPEG_MAX_COMP 3

#define JPEG_OK                0
#define JPEG_ERR_ARG          -1   /* bad argument / inconsistent jpeg_image */
#define JPEG_ERR_FORMAT       -2   /* not a JPEG or broken marker structure */
#define JPEG_ERR_UNSUPPORTED  -3   /* progressive, 12-bit, arithmetic, CMYK, ... */
#define JPEG_ERR_DATA         -4   /* corrupt entropy data (bad Huffman code ...) */
#define JPEG_ERR_TRUNC        -5   /* entropy data ended early / missing restart */
#define JPEG_ERR_ARENA        -6   /* arena too small */
#define JPEG_ERR_OVERFLOW     -7   /* encoder output buffer too small */
#define JPEG_ERR_STATE        -8   /* streaming API misuse (e.g. fini before all bands) */
#define JPEG_ERR_IO           -9   /* read/write callback failed */

/* Transform mode of the band API (see jpeg_sdec_set_xform / jpeg_senc_set_xform):
 *   JPEG_XFORM_ACCURATE  islow IDCT / FDCT, bit-exact with libjpeg (default)
 *   JPEG_XFORM_FAST      AAN IDCT / FDCT with the quantiser fused into the forward DCT. Not
 *                        bit-exact: on the Sony frames the roundtrip stays at 62.7 dB luma PSNR
 *                        (63.0 dB accurate), +-1 level; worst case over all test material
 *                        55 dB / +-3. Pixel components only (passthrough components are untouched).
 * The exact optimisations (sparse IDCT dispatch, combined (run,value) AC Huffman lookup, dequantising
 * at decode time, cheaper exact quantiser, faster bit writer) are ALWAYS on and do not change a
 * single output byte (verified bit-identical to the build before the speed work).
 * Select at run time with jpeg_sdec_set_xform()/jpeg_senc_set_xform() (decoder and encoder are
 * independent), or build with -DSWJPEG_DEFAULT_XFORM=1 to make the fast mode the default. */
#define JPEG_XFORM_ACCURATE 0
#define JPEG_XFORM_FAST     1
#ifndef SWJPEG_DEFAULT_XFORM
#define SWJPEG_DEFAULT_XFORM JPEG_XFORM_ACCURATE
#endif

/* Callback I/O buffer sizes (bytes). Override at build time with -DJPEG_RD_BUF=... if the
 * storage layer prefers other chunk sizes. */
#ifndef JPEG_RD_BUF
#define JPEG_RD_BUF 4096   /* input: bytes requested per read callback call */
#endif
#ifndef JPEG_WR_BUF
#define JPEG_WR_BUF 4096   /* output: bytes buffered per write callback call */
#endif

/* Sequential input: copy up to len bytes to buf, return the number of bytes copied
 * (fewer than len is fine), 0 at end of file, < 0 on error. */
typedef long (*jpeg_read_fn)(void *ctx, unsigned char *buf, unsigned long len);
/* Sequential output: consume len bytes, return len (a smaller positive count is retried
 * with the remainder), <= 0 means error. */
typedef long (*jpeg_write_fn)(void *ctx, const unsigned char *buf, unsigned long len);

typedef struct jpeg_comp {
    unsigned char *data;   /* plane, row-major, 8-bit samples (32-byte aligned) */
    int stride;            /* bytes per row (== pw for decoder output) */
    int width, height;     /* visible samples: ceil(W*h/hmax) x ceil(H*v/vmax)  (decoder fills) */
    int pw, ph;            /* allocated, MCU-padded samples/rows (decoder fills)  */
    int h, v;              /* sampling factors from SOF (Y 2x1 => 4:2:2)          */
    int tq;                /* index (0..3) into jpeg_image.qt                      */
    int y0;                /* band API: absolute row (in THIS component's plane) of the
                              first row of the band; whole-frame API: 0              */
    int coef;              /* band API: 1 = this band holds QUANTISED coefficient blocks
                              (see JPEG_COEF_*), 0 = 8-bit pixels (decoder fills)    */
} jpeg_comp;

typedef struct jpeg_image {
    int width, height;             /* image size in pixels (Y plane visible size)      */
    int ncomp;                     /* 1 (grey) or 3 (Y, Cb, Cr)                         */
    int hmax, vmax;                /* max sampling factors (decoder fills)              */
    int restart_interval;          /* DRI in MCUs, 0 = none. Decoder: parsed value.
                                      Encoder: if > 0, emits DRI + RSTn markers.        */
    jpeg_comp comp[JPEG_MAX_COMP];
    unsigned short qt[4][64];      /* quantisation tables, ZIGZAG order exactly as in
                                      DQT, already widened to 16 bit. Decoder fills the
                                      ones present in the file; encoder uses qt[comp.tq]. */
} jpeg_image;

/*
 * Exact arena size (bytes) jpeg_decode() needs for this file, or 0 if the SOF
 * cannot be found / is unsupported. Only the headers are parsed (fast).
 */
unsigned long jpeg_decode_arena_size(const unsigned char *in, unsigned long inlen);

/*
 * Decode the FIRST frame of a baseline (SOF0/SOF1 8-bit Huffman) JPEG. All APPn
 * and COM segments are skipped, decoding stops at the first EOI (so MPO files
 * are fine). Supports 1 or 3 components, any integer sampling ratio (4:4:4,
 * 4:2:2, 4:2:0, 4:4:0, 4:1:1 ...), DRI/RSTn, multiple scans.
 * Returns JPEG_OK or a negative JPEG_ERR_*. On success out->comp[i].data point
 * into `arena`.
 */
int jpeg_decode(const unsigned char *in, unsigned long inlen,
                void *arena, unsigned long arenalen, jpeg_image *out);

/* Scratch bytes jpeg_encode() needs (constant). */
unsigned long jpeg_encode_arena_size(void);

/*
 * Encode a baseline sequential JPEG (SOI, JFIF APP0, DQT, SOF0, DHT x4 with the
 * Annex K tables, [DRI], SOS, entropy data, EOI) straight from the YCbCr planes.
 * Quantisation tables = img->qt[comp.tq], sampling = comp.h/comp.v: pass the
 * jpeg_image that jpeg_decode() filled (optionally with modified plane samples)
 * for a minimal-generation-loss roundtrip.
 * *outlen: on entry = capacity of `out`; on return = bytes written.
 * Returns JPEG_OK, JPEG_ERR_OVERFLOW if `out` is too small, or another error.
 */
int jpeg_encode(const jpeg_image *img, void *arena, unsigned long arenalen,
                unsigned char *out, unsigned long *outlen);


/* ========================================================================== *
 * STREAMING (band-at-a-time) API  -  O(width) memory instead of O(width*height)
 * ========================================================================== *
 * A band is ONE MCU row, top to bottom:
 *     luma rows per band   = vmax*8      (4:2:2 / 4:4:4: 8,  4:2:0: 16)
 *     chroma rows per band = v_c*8       (4:2:2 / 4:2:0 / 4:4:4: 8)
 *     band stride          = pw          (= mcus_x*h*8; 4912 luma / 2456 chroma for the
 *                                         4912x3264 4:2:2 fixture)
 * The decoder owns the band buffers (inside `scratch`); they are overwritten by the next
 * jpeg_sdec_band() call, so process a band (e.g. add grain) and hand it to
 * jpeg_senc_band() BEFORE decoding the next one:
 *
 *     jpeg_image meta; jpeg_sdec d; jpeg_senc e; jpeg_comp band[3]; int rows;
 *     jpeg_sdec_init(in, inlen, dscratch, dlen, &d, &meta);
 *     jpeg_senc_init(out, &cap, &meta, escratch, elen, &e);   // cap = capacity of out
 *     while ((rows = jpeg_sdec_band(&d, band)) > 0) {
 *         // modify band[0].data (Y), rows 0..rows-1 and columns 0..band[0].width-1,
 *         // absolute luma row of band row r = band[0].y0 + r
 *         jpeg_senc_band(&e, band);
 *     }
 *     if (rows < 0) ... error ...
 *     jpeg_senc_fini(&e, &outlen);                            // flush + EOI, outlen = bytes
 *
 * Each band is encoded in full (all 8*v rows incl. padding), so only touch visible
 * rows/columns. The encoder reuses the INPUT's quant tables, sampling factors and
 * restart interval (taken from `meta`) and writes the same Annex K Huffman tables as the
 * whole-frame jpeg_encode(); with unmodified bands the output is BYTE-IDENTICAL to
 * jpeg_encode(jpeg_decode()).
 * Limits: baseline, 1 or 3 components, ONE interleaved scan (what cameras write);
 * multi-scan baseline files return JPEG_ERR_UNSUPPORTED (they need whole planes).
 * `in` must stay readable during the whole decode; `out` receives the whole JPEG.
 */
typedef struct jpeg_sdec { void *ctx; } jpeg_sdec;
typedef struct jpeg_senc { void *ctx; } jpeg_senc;

/* Select the transform for this decoder (call after init, before the first band).
 * JPEG_OK, or JPEG_ERR_STATE if a band was already decoded, JPEG_ERR_ARG for a bad mode. */
int jpeg_sdec_set_xform(jpeg_sdec *d, int mode);
/* Same for the encoder (after init, before the first band). */
int jpeg_senc_set_xform(jpeg_senc *e, int mode);

/* Exact scratch bytes jpeg_sdec_init() needs (incl. alignment slack), 0 on error. */
unsigned long jpeg_sdec_scratch_size(const unsigned char *in, unsigned long inlen);

/*
 * Parse headers up to the first SOS, set up the Huffman tables and band buffers.
 * meta (output): width/height/ncomp/hmax/vmax/restart_interval/qt/comp[i].{h,v,tq,
 * width,height,pw,ph,stride} describe the FULL frame; comp[i].data is NULL.
 */
int jpeg_sdec_init(const unsigned char *in, unsigned long inlen,
                   void *scratch, unsigned long slen, jpeg_sdec *d, jpeg_image *meta);

/*
 * Decode the next MCU row. bands[0..ncomp-1] are filled (bands[ncomp..2] zeroed):
 *     data    top-left of the band buffer      stride  row pitch (bytes)
 *     width   visible samples per row          height  VISIBLE rows in this band (<= ph)
 *     pw      padded width (== stride)         ph      allocated rows (8*v)
 *     y0      absolute row of the band's first row in that component's plane
 *     h, v, tq  as in meta
 * Returns the number of visible LUMA rows in the band (vmax*8, fewer in the last band),
 * 0 after the last band, or a negative JPEG_ERR_* (sticky).
 */
int jpeg_sdec_band(jpeg_sdec *d, jpeg_comp bands[JPEG_MAX_COMP]);

/*
 * Start a streaming encode: writes SOI, JFIF APP0, DQT, SOF0, DHT, [DRI], SOS into `out`
 * from `meta`. *outlen = capacity of `out` on entry (not modified here).
 * scratch: jpeg_encode_arena_size() bytes.
 */
int jpeg_senc_init(unsigned char *out, unsigned long *outlen, const jpeg_image *meta,
                   void *scratch, unsigned long slen, jpeg_senc *e);

/* Encode one band (exactly what jpeg_sdec_band() returned; needs data, stride >= pw and
 * ph >= 8*v per component) and append it to `out`. JPEG_ERR_OVERFLOW if `out` is full,
 * JPEG_ERR_ARG on bad bands or more bands than the image has. */
int jpeg_senc_band(jpeg_senc *e, const jpeg_comp bands[JPEG_MAX_COMP]);

/* Flush, write EOI, *outlen = total bytes in `out`. JPEG_ERR_STATE if not every MCU row
 * of the frame was encoded. */
int jpeg_senc_fini(jpeg_senc *e, unsigned long *outlen);


/* ========================================================================== *
 * STREAMING I/O (callbacks): neither the source JPEG nor the output JPEG is held in RAM
 * ========================================================================== *
 * Same band flow as above; the decoder PULLS source bytes through a read callback and the
 * encoder PUSHES output bytes through a write callback:
 *
 *     jpeg_read_fn  rd = ...;   // e.g. Fsys_Read of the original file, sequential from offset 0
 *     jpeg_write_fn wr = ...;   // e.g. Fsys_Write of the temp file
 *     rc = jpeg_sdec_init_cb(rd, rctx, dscr, dlen, &d, &meta);
 *     if (rc == JPEG_ERR_ARENA) {            // dlen too small for the bands; meta IS valid:
 *         dlen = jpeg_sdec_cb_scratch_size(&meta);      // size the scratch, REWIND the source
 *         ... rc = jpeg_sdec_init_cb(rd, rctx, dscr, dlen, &d, &meta);     // and call again
 *     }
 *     jpeg_senc_init_cb(wr, wctx, &meta, escr, elen, &e);   // header goes out at once
 *     while ((rows = jpeg_sdec_band(&d, band)) > 0) { ...edit band...; jpeg_senc_band(&e, band); }
 *     jpeg_senc_fini(&e, &total);                           // flushes the tail, total = bytes written
 *
 * Extra memory vs. the whole-buffer streaming API (all inside the scratch you pass):
 *     decoder: JPEG_RD_BUF + 16 = 4112 bytes refill buffer (+4128 B scratch after alignment;
 *              read requests are JPEG_RD_BUF=4096 bytes; DQT/DHT/SOF/DRI/SOS segments must
 *              fit in the buffer (valid ones are < 2.2 KB, longer ones give
 *              JPEG_ERR_UNSUPPORTED), APPn/COM of any size are skipped by reading and
 *              discarding)
 *     encoder: JPEG_WR_BUF = 4096 bytes (+4096 B scratch; the write callback gets <= 4096-byte
 *              chunks, the last one shorter)
 * Measured, 4912x3264: 4:2:2 decoder 98,016 + encoder 10,496 = 108,512 bytes;
 *                      4:2:0 / 4:4:4 decoder 137,312 + encoder 10,496 = 147,808 bytes.
 * (whole-buffer streaming: 4:2:2 decoder 93,888 + encoder 6,400 = 100,288 bytes.)
 * With chroma passthrough (JPEG_COEF_CHROMA) the callback decoder needs 137,312 (4:2:2),
 * 176,608 (4:2:0), 215,904 (4:4:4) bytes.
 * Header scan: the Exif APP1 (any size) is read through the ring and dropped; the decoder
 * never reads past what it needs (at most one chunk beyond the last entropy byte it uses).
 * The output is byte-identical to the whole-buffer streaming API.
 * Errors: a read/write callback failure is reported as JPEG_ERR_IO (sticky).
 */

/* Minimum scratch for jpeg_sdec_init_cb() to read the headers (constant). */
unsigned long jpeg_sdec_cb_min_scratch(void);
/* Scratch needed for the whole frame in callback mode (needs a filled `meta`). 0 on error. */
unsigned long jpeg_sdec_cb_scratch_size(const jpeg_image *meta);
/* Scratch for jpeg_senc_init_cb() (constant). */
unsigned long jpeg_senc_cb_scratch_size(void);

/*
 * Like jpeg_sdec_init() but reads the JPEG through rd (sequentially from its first byte).
 * Returns JPEG_ERR_ARENA with `meta` filled when the scratch is too small for the band
 * buffers (the source has been consumed: rewind it before the retry).
 */
int jpeg_sdec_init_cb(jpeg_read_fn rd, void *rd_ctx, void *scratch, unsigned long slen,
                      jpeg_sdec *d, jpeg_image *meta);

/*
 * Like jpeg_senc_init() but the output goes through wr (SOI..SOS now, the rest per band and
 * at jpeg_senc_fini(), which also returns the total number of bytes written).
 */
int jpeg_senc_init_cb(jpeg_write_fn wr, void *wr_ctx, const jpeg_image *meta,
                      void *scratch, unsigned long slen, jpeg_senc *e);


/* ========================================================================== *
 * COEFFICIENT PASSTHROUGH for components the caller does not edit
 * ========================================================================== *
 * With film grain only luma changes. Decoding chroma to pixels and encoding it again costs an
 * IDCT, a forward DCT and a quantiser per block and loses a little precision. Instead the decoder
 * can hand such components over as the quantised coefficients straight from the Huffman decoder,
 * and jpeg_senc_band() entropy-codes them back unchanged: no transform, no quantiser, and the
 * chroma of the output is bit-identical to the input.
 *
 *     scratch = jpeg_sdec_cb_scratch_size_ex(&meta, JPEG_COEF_CHROMA);
 *     jpeg_sdec_init_cb_ex(rd, rctx, scratch, slen, JPEG_COEF_CHROMA, &d, &meta);
 *     ... the loop is unchanged; edit only band[0] (Y). band[1], band[2] have .coef = 1 and the
 *         caller must leave them alone (or just pass them to jpeg_senc_band) ...
 *
 * A coefficient band holds, for the component, (pw/8) x v blocks of 64 int16 in ZIGZAG order
 * (quantised values, DC absolute, not a difference); block (r, c) of the band starts at
 * (char *)data + r * stride + c * 128, stride = (pw/8) * 128 bytes. It needs twice the memory of
 * the pixel band. The encoder re-uses meta.qt, so do not change meta.qt of a passthrough
 * component between decode and encode. */
#define JPEG_COEF_Y      1u
#define JPEG_COEF_CB     2u
#define JPEG_COEF_CR     4u
#define JPEG_COEF_CHROMA (JPEG_COEF_CB | JPEG_COEF_CR)

/* *_ex variants of the init/size functions; opts = OR of JPEG_COEF_* (0 = all components are pixels) */
unsigned long jpeg_sdec_scratch_size_ex(const unsigned char *in, unsigned long inlen, unsigned opts);
int jpeg_sdec_init_ex(const unsigned char *in, unsigned long inlen, void *scratch, unsigned long slen,
                      unsigned opts, jpeg_sdec *d, jpeg_image *meta);
unsigned long jpeg_sdec_cb_scratch_size_ex(const jpeg_image *meta, unsigned opts);
int jpeg_sdec_init_cb_ex(jpeg_read_fn rd, void *rd_ctx, void *scratch, unsigned long slen,
                         unsigned opts, jpeg_sdec *d, jpeg_image *meta);

#ifdef __cplusplus
}
#endif
#endif /* SWJPEG_H */

/*
 * swjpeg.c - freestanding, integer-only baseline JPEG codec for ARMv5TE.
 *
 *   arm-linux-gnueabi-gcc -march=armv5te -nostdlib -fPIC -c swjpeg.c
 *
 * Rules this file obeys (so that the object has NO undefined symbols except
 * _GLOBAL_OFFSET_TABLE_, which the linker defines for any -fPIC link):
 *   - no libc, no libgcc: own memset/memcpy/memmove/memcmp (static)
 *   - no float/double
 *   - NO integer division / modulo by a variable (ARMv5 has no divider, that
 *     would pull __aeabi_uidiv); setup code uses udiv32(), hot paths use
 *     shifts and reciprocal multiplication (umull is native on ARMv5TE)
 *   - no 64-bit division, no variable 64-bit shifts
 *   - no writable globals, no pointer tables in .rodata (=> no run-time relocs)
 *   - no malloc/stdio/syscalls: pure functions on caller buffers
 *   - no unaligned word access (ARMv5 rotates unaligned loads)
 *
 * Transforms: IJG "islow" integer IDCT (jidctint) and integer forward DCT
 * (jfdctint), 13-bit constants, 2 extra pass-1 bits. The decoder is bit-exact
 * with libjpeg(-turbo) JDCT_ISLOW for valid streams.
 */
/* O2 even if the caller forgets -O; no loop->memset idiom conversion (own memset must not
 * call itself); wrapv: IDCT/FDCT arithmetic on CORRUPT input may overflow int32 - with wrapv
 * that is defined (wraps, output is garbage but memory-safe), exactly like on real ARM. */
#pragma GCC optimize ("O2", "no-tree-loop-distribute-patterns", "wrapv")

#include "swjpeg.h"

typedef unsigned char      u8;
typedef unsigned short     u16;
typedef short              i16;
typedef unsigned int       u32;
typedef int                i32;
typedef unsigned long long u64;
typedef __SIZE_TYPE__      sw_size;

/* hot helpers are forced inline so the object is fast even when built WITHOUT -O */
#define SW_INLINE static inline __attribute__((always_inline))

/* ========================================================================= */
/* own mem* (static; also satisfies any compiler-generated libcalls)          */
/* ========================================================================= */

__attribute__((used)) static void *memset(void *d, int c, sw_size n)
{
    u8 *p = (u8 *)d;
    u32 w = (u8)c;
    w |= w << 8; w |= w << 16;
    while (n && ((unsigned long)p & 3)) { *p++ = (u8)c; n--; }
    while (n >= 4) { *(u32 *)(void *)p = w; p += 4; n -= 4; }
    while (n) { *p++ = (u8)c; n--; }
    return d;
}

__attribute__((used)) static void *memcpy(void *d, const void *s, sw_size n)
{
    u8 *dp = (u8 *)d;
    const u8 *sp = (const u8 *)s;
    if ((((unsigned long)dp | (unsigned long)sp) & 3) == 0) {
        while (n >= 4) { *(u32 *)(void *)dp = *(const u32 *)(const void *)sp; dp += 4; sp += 4; n -= 4; }
    }
    while (n) { *dp++ = *sp++; n--; }
    return d;
}

__attribute__((used)) static void *memmove(void *d, const void *s, sw_size n)
{
    u8 *dp = (u8 *)d;
    const u8 *sp = (const u8 *)s;
    if (dp == sp || n == 0) return d;
    if (dp < sp || dp >= sp + n) return memcpy(d, s, n);
    dp += n; sp += n;
    while (n--) *--dp = *--sp;
    return d;
}

__attribute__((used)) static int memcmp(const void *a, const void *b, sw_size n)
{
    const u8 *x = (const u8 *)a, *y = (const u8 *)b;
    while (n--) {
        if (*x != *y) return (int)*x - (int)*y;
        x++; y++;
    }
    return 0;
}

/* ========================================================================= */
/* small helpers                                                             */
/* ========================================================================= */

/* software divide, setup code only (ARMv5 has no divide instruction) */
static u32 udiv32(u32 n, u32 d)
{
    u32 q = 0, r = 0;
    int i;
    for (i = 31; i >= 0; i--) {
        r = (r << 1) | ((n >> i) & 1u);
        if (r >= d) { r -= d; q |= 1u << i; }
    }
    return q;
}

static u32 cdiv(u32 a, u32 b) { return udiv32(a + b - 1u, b); }

static u32 align32(u32 x) { return (x + 31u) & ~31u; }

SW_INLINE int bitlen(u32 x) { return x ? 32 - __builtin_clz(x) : 0; }

SW_INLINE u8 clamp8(i32 x)
{
    if ((u32)x > 255u) x = (x < 0) ? 0 : 255;
    return (u8)x;
}

/* zigzag position -> natural (row-major) index */
static const u8 zz[64] = {
     0,  1,  8, 16,  9,  2,  3, 10,
    17, 24, 32, 25, 18, 11,  4,  5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13,  6,  7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63
};

static const u8 zz_rowhi[64] = {
    0, 0, 1, 2, 2, 2, 2, 2, 2, 3, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7
};

static const u8 zz_colhi[64] = {
    0, 1, 1, 1, 1, 2, 3, 3, 3, 3, 3, 3, 3, 3, 4, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7
};


/* AAN row/column scale factors a_k = cos(k*pi/16)*sqrt(2) (a_0 = 1) in Q14 */
static const u16 aan14[8] = { 16384, 22725, 21407, 19266, 16384, 12873, 8867, 4520 };

/* ========================================================================= */
/* IJG islow transforms                                                      */
/* ========================================================================= */

#define CONST_BITS 13
#define PASS1_BITS 2
#define FIX_0_298631336  2446
#define FIX_0_390180644  3196
#define FIX_0_541196100  4433
#define FIX_0_765366865  6270
#define FIX_0_899976223  7373
#define FIX_1_175875602  9633
#define FIX_1_501321110 12299
#define FIX_1_847759065 15137
#define FIX_1_961570560 16069
#define FIX_2_053119869 16819
#define FIX_2_562915447 20995
#define FIX_3_072711026 25172
#define DESCALE(x, n) (((x) + ((i32)1 << ((n) - 1))) >> (n))

/*
 * Exact islow IDCT (bit-identical to libjpeg JDCT_ISLOW), specialised on the occupied corner of
 * the coefficient block: NR = 4 means rows 4..7 are known to be zero, NC = 4 means columns 4..7
 * are. The zero inputs become literals, so the compiler removes their share of the arithmetic
 * without changing a single output bit. in[] holds the already dequantised coefficients.
 */
SW_INLINE void islow_col(const i32 *ip, i32 *wp, const int NR)
{
    i32 i0 = ip[0], i1 = ip[8], i2 = ip[16], i3 = ip[24];
    i32 i4 = NR > 4 ? ip[32] : 0, i5 = NR > 4 ? ip[40] : 0, i6 = NR > 4 ? ip[48] : 0, i7 = NR > 4 ? ip[56] : 0;
    i32 tmp0, tmp1, tmp2, tmp3, tmp10, tmp11, tmp12, tmp13, z1, z2, z3, z4, z5;

    if (!(i1 | i2 | i3 | i4 | i5 | i6 | i7)) {
        i32 dc = i0 * (1 << PASS1_BITS);
        wp[0] = wp[8] = wp[16] = wp[24] = wp[32] = wp[40] = wp[48] = wp[56] = dc;
        return;
    }
    z2 = i2; z3 = i6;
    z1 = (z2 + z3) * FIX_0_541196100;
    tmp2 = z1 + z3 * (-FIX_1_847759065);
    tmp3 = z1 + z2 * FIX_0_765366865;
    z2 = i0; z3 = i4;
    tmp0 = (z2 + z3) * (1 << CONST_BITS);
    tmp1 = (z2 - z3) * (1 << CONST_BITS);
    tmp10 = tmp0 + tmp3; tmp13 = tmp0 - tmp3;
    tmp11 = tmp1 + tmp2; tmp12 = tmp1 - tmp2;

    tmp0 = i7; tmp1 = i5; tmp2 = i3; tmp3 = i1;
    z1 = tmp0 + tmp3; z2 = tmp1 + tmp2; z3 = tmp0 + tmp2; z4 = tmp1 + tmp3;
    z5 = (z3 + z4) * FIX_1_175875602;
    tmp0 *= FIX_0_298631336; tmp1 *= FIX_2_053119869;
    tmp2 *= FIX_3_072711026; tmp3 *= FIX_1_501321110;
    z1 *= -FIX_0_899976223; z2 *= -FIX_2_562915447;
    z3 *= -FIX_1_961570560; z4 *= -FIX_0_390180644;
    z3 += z5; z4 += z5;
    tmp0 += z1 + z3; tmp1 += z2 + z4; tmp2 += z2 + z3; tmp3 += z1 + z4;

    wp[0]  = DESCALE(tmp10 + tmp3, CONST_BITS - PASS1_BITS);
    wp[56] = DESCALE(tmp10 - tmp3, CONST_BITS - PASS1_BITS);
    wp[8]  = DESCALE(tmp11 + tmp2, CONST_BITS - PASS1_BITS);
    wp[48] = DESCALE(tmp11 - tmp2, CONST_BITS - PASS1_BITS);
    wp[16] = DESCALE(tmp12 + tmp1, CONST_BITS - PASS1_BITS);
    wp[40] = DESCALE(tmp12 - tmp1, CONST_BITS - PASS1_BITS);
    wp[24] = DESCALE(tmp13 + tmp0, CONST_BITS - PASS1_BITS);
    wp[32] = DESCALE(tmp13 - tmp0, CONST_BITS - PASS1_BITS);
}

SW_INLINE void islow_row(const i32 *wp, u8 *out, const int NC)
{
    i32 w0 = wp[0], w1 = wp[1], w2 = wp[2], w3 = wp[3];
    i32 w4 = NC > 4 ? wp[4] : 0, w5 = NC > 4 ? wp[5] : 0, w6 = NC > 4 ? wp[6] : 0, w7 = NC > 4 ? wp[7] : 0;
    i32 tmp0, tmp1, tmp2, tmp3, tmp10, tmp11, tmp12, tmp13, z1, z2, z3, z4, z5;

    if (!(w1 | w2 | w3 | w4 | w5 | w6 | w7)) {
        u8 dcv = clamp8(DESCALE(w0, PASS1_BITS + 3) + 128);
        out[0] = out[1] = out[2] = out[3] = out[4] = out[5] = out[6] = out[7] = dcv;
        return;
    }
    z2 = w2; z3 = w6;
    z1 = (z2 + z3) * FIX_0_541196100;
    tmp2 = z1 + z3 * (-FIX_1_847759065);
    tmp3 = z1 + z2 * FIX_0_765366865;
    tmp0 = (w0 + w4) * (1 << CONST_BITS);
    tmp1 = (w0 - w4) * (1 << CONST_BITS);
    tmp10 = tmp0 + tmp3; tmp13 = tmp0 - tmp3;
    tmp11 = tmp1 + tmp2; tmp12 = tmp1 - tmp2;

    tmp0 = w7; tmp1 = w5; tmp2 = w3; tmp3 = w1;
    z1 = tmp0 + tmp3; z2 = tmp1 + tmp2; z3 = tmp0 + tmp2; z4 = tmp1 + tmp3;
    z5 = (z3 + z4) * FIX_1_175875602;
    tmp0 *= FIX_0_298631336; tmp1 *= FIX_2_053119869;
    tmp2 *= FIX_3_072711026; tmp3 *= FIX_1_501321110;
    z1 *= -FIX_0_899976223; z2 *= -FIX_2_562915447;
    z3 *= -FIX_1_961570560; z4 *= -FIX_0_390180644;
    z3 += z5; z4 += z5;
    tmp0 += z1 + z3; tmp1 += z2 + z4; tmp2 += z2 + z3; tmp3 += z1 + z4;

#define SH (CONST_BITS + PASS1_BITS + 3)
    out[0] = clamp8(DESCALE(tmp10 + tmp3, SH) + 128);
    out[7] = clamp8(DESCALE(tmp10 - tmp3, SH) + 128);
    out[1] = clamp8(DESCALE(tmp11 + tmp2, SH) + 128);
    out[6] = clamp8(DESCALE(tmp11 - tmp2, SH) + 128);
    out[2] = clamp8(DESCALE(tmp12 + tmp1, SH) + 128);
    out[5] = clamp8(DESCALE(tmp12 - tmp1, SH) + 128);
    out[3] = clamp8(DESCALE(tmp13 + tmp0, SH) + 128);
    out[4] = clamp8(DESCALE(tmp13 - tmp0, SH) + 128);
#undef SH
}

SW_INLINE void idct_islow_t(const i32 *in, u8 *out, int stride, const int NR, const int NC)
{
    i32 ws[64];
    int c, r;
    for (c = 0; c < NC; c++) islow_col(in + c, ws + c, NR);
    for (r = 0; r < 8; r++, out += stride) islow_row(ws + r * 8, out, NC);
}
static void idct_islow_44(const i32 *in, u8 *out, int stride) { idct_islow_t(in, out, stride, 4, 4); }
static void idct_islow_48(const i32 *in, u8 *out, int stride) { idct_islow_t(in, out, stride, 4, 8); }
static void idct_islow_84(const i32 *in, u8 *out, int stride) { idct_islow_t(in, out, stride, 8, 4); }
static void idct_islow_88(const i32 *in, u8 *out, int stride) { idct_islow_t(in, out, stride, 8, 8); }

/*
 * FAST transform mode, decoder side: AAN IDCT, 5 multiplies per 1-D pass instead of 12. The AAN
 * scale factors are folded into the dequantisation multipliers (qm, Q5 fixed point), so the
 * 1-D passes multiply only by 4 constants. Not bit-exact with libjpeg (about +-1 level on a few
 * percent of the samples), irrelevant when grain is added on top.
 */
#define AAN_FB   5                                   /* fractional bits of the dequantised coefficients */
#define QSH      5                                   /* qm carries QSH extra fractional bits (precision for q=1 at high frequencies) */
#define AAN_R1   2                                   /* bits dropped between the passes            */
#define AAN_SH   (AAN_FB - AAN_R1 + 3)               /* final descale                              */
#define AAN_BIAS ((1 << (AAN_SH - 1)) + (128 << AAN_SH))   /* rounding + level shift, added to DC  */
#define IMUL(v, c) (((v) * (c) + 1024) >> 11)

#define AAN_IDCT_1D(i0, i1, i2, i3, i4, i5, i6, i7, o0, o1, o2, o3, o4, o5, o6, o7) do { \
    i32 t0 = (i0), t1 = (i2), t2 = (i4), t3 = (i6); \
    i32 t10 = t0 + t2, t11 = t0 - t2, t13 = t1 + t3, t12 = IMUL(t1 - t3, 2896) - t13; \
    i32 t4, t5, t6, t7, z5, z10, z11, z12, z13; \
    t0 = t10 + t13; t3 = t10 - t13; t1 = t11 + t12; t2 = t11 - t12; \
    t4 = (i1); t5 = (i3); t6 = (i5); t7 = (i7); \
    z13 = t6 + t5; z10 = t6 - t5; z11 = t4 + t7; z12 = t4 - t7; \
    t7 = z11 + z13; t11 = IMUL(z11 - z13, 2896); \
    z5 = IMUL(z10 + z12, 3784); t10 = IMUL(z12, 2217) - z5; t12 = IMUL(z10, -5352) + z5; \
    t6 = t12 - t7; t5 = t11 - t6; t4 = t10 + t5; \
    o0 = t0 + t7; o1 = t1 + t6; o2 = t2 + t5; o3 = t3 - t4; o4 = t3 + t4; o5 = t2 - t5; o6 = t1 - t6; o7 = t0 - t7; \
} while (0)

SW_INLINE void aan_col(const i32 *ip, i32 *wp, const int NR)
{
    i32 i0 = ip[0], i1 = ip[8], i2 = ip[16], i3 = ip[24];
    i32 i4 = NR > 4 ? ip[32] : 0, i5 = NR > 4 ? ip[40] : 0, i6 = NR > 4 ? ip[48] : 0, i7 = NR > 4 ? ip[56] : 0;
    i32 o0, o1, o2, o3, o4, o5, o6, o7;

    if (!(i1 | i2 | i3 | i4 | i5 | i6 | i7)) {
        i32 dc = (i0 + (1 << (AAN_R1 - 1))) >> AAN_R1;
        wp[0] = wp[8] = wp[16] = wp[24] = wp[32] = wp[40] = wp[48] = wp[56] = dc;
        return;
    }
    AAN_IDCT_1D(i0 + (1 << (AAN_R1 - 1)), i1, i2, i3, i4, i5, i6, i7, o0, o1, o2, o3, o4, o5, o6, o7);
    wp[0] = o0 >> AAN_R1;  wp[8] = o1 >> AAN_R1;  wp[16] = o2 >> AAN_R1; wp[24] = o3 >> AAN_R1;
    wp[32] = o4 >> AAN_R1; wp[40] = o5 >> AAN_R1; wp[48] = o6 >> AAN_R1; wp[56] = o7 >> AAN_R1;
}

SW_INLINE void aan_row(const i32 *wp, u8 *out, const int NC)
{
    i32 w0 = wp[0] + AAN_BIAS, w1 = wp[1], w2 = wp[2], w3 = wp[3];
    i32 w4 = NC > 4 ? wp[4] : 0, w5 = NC > 4 ? wp[5] : 0, w6 = NC > 4 ? wp[6] : 0, w7 = NC > 4 ? wp[7] : 0;
    i32 o0, o1, o2, o3, o4, o5, o6, o7;

    if (!(w1 | w2 | w3 | w4 | w5 | w6 | w7)) {
        u8 v = clamp8(w0 >> AAN_SH);
        out[0] = out[1] = out[2] = out[3] = out[4] = out[5] = out[6] = out[7] = v;
        return;
    }
    AAN_IDCT_1D(w0, w1, w2, w3, w4, w5, w6, w7, o0, o1, o2, o3, o4, o5, o6, o7);
    out[0] = clamp8(o0 >> AAN_SH); out[1] = clamp8(o1 >> AAN_SH); out[2] = clamp8(o2 >> AAN_SH); out[3] = clamp8(o3 >> AAN_SH);
    out[4] = clamp8(o4 >> AAN_SH); out[5] = clamp8(o5 >> AAN_SH); out[6] = clamp8(o6 >> AAN_SH); out[7] = clamp8(o7 >> AAN_SH);
}

SW_INLINE void idct_aan_t(const i32 *in, u8 *out, int stride, const int NR, const int NC)
{
    i32 ws[64];
    int c, r;
    for (c = 0; c < NC; c++) aan_col(in + c, ws + c, NR);
    for (r = 0; r < 8; r++, out += stride) aan_row(ws + r * 8, out, NC);
}
static void idct_aan_44(const i32 *in, u8 *out, int stride) { idct_aan_t(in, out, stride, 4, 4); }
static void idct_aan_48(const i32 *in, u8 *out, int stride) { idct_aan_t(in, out, stride, 4, 8); }
static void idct_aan_84(const i32 *in, u8 *out, int stride) { idct_aan_t(in, out, stride, 8, 4); }
static void idct_aan_88(const i32 *in, u8 *out, int stride) { idct_aan_t(in, out, stride, 8, 8); }

/* Forward DCT (islow). src: 8x8 u8 samples. ws: result, scaled by 8
 * (same convention as libjpeg's workspace before quantisation). */
static void fdct_block(const u8 *src, int stride, i32 *ws)
{
    int r, c;
    i32 tmp0, tmp1, tmp2, tmp3, tmp4, tmp5, tmp6, tmp7;
    i32 tmp10, tmp11, tmp12, tmp13, z1, z2, z3, z4, z5;

    for (r = 0; r < 8; r++, src += stride) {
        i32 *dp = ws + r * 8;
        tmp0 = (i32)src[0] + src[7]; tmp7 = (i32)src[0] - src[7];
        tmp1 = (i32)src[1] + src[6]; tmp6 = (i32)src[1] - src[6];
        tmp2 = (i32)src[2] + src[5]; tmp5 = (i32)src[2] - src[5];
        tmp3 = (i32)src[3] + src[4]; tmp4 = (i32)src[3] - src[4];
        /* level shift: sum of 8 samples carries 8*128 in tmp10+tmp11 */
        tmp10 = tmp0 + tmp3; tmp13 = tmp0 - tmp3;
        tmp11 = tmp1 + tmp2; tmp12 = tmp1 - tmp2;
        dp[0] = (tmp10 + tmp11 - 8 * 128) * (1 << PASS1_BITS);
        dp[4] = (tmp10 - tmp11) * (1 << PASS1_BITS);
        z1 = (tmp12 + tmp13) * FIX_0_541196100;
        dp[2] = DESCALE(z1 + tmp13 * FIX_0_765366865, CONST_BITS - PASS1_BITS);
        dp[6] = DESCALE(z1 + tmp12 * (-FIX_1_847759065), CONST_BITS - PASS1_BITS);
        z1 = tmp4 + tmp7; z2 = tmp5 + tmp6; z3 = tmp4 + tmp6; z4 = tmp5 + tmp7;
        z5 = (z3 + z4) * FIX_1_175875602;
        tmp4 *= FIX_0_298631336; tmp5 *= FIX_2_053119869;
        tmp6 *= FIX_3_072711026; tmp7 *= FIX_1_501321110;
        z1 *= -FIX_0_899976223; z2 *= -FIX_2_562915447;
        z3 *= -FIX_1_961570560; z4 *= -FIX_0_390180644;
        z3 += z5; z4 += z5;
        dp[7] = DESCALE(tmp4 + z1 + z3, CONST_BITS - PASS1_BITS);
        dp[5] = DESCALE(tmp5 + z2 + z4, CONST_BITS - PASS1_BITS);
        dp[3] = DESCALE(tmp6 + z2 + z3, CONST_BITS - PASS1_BITS);
        dp[1] = DESCALE(tmp7 + z1 + z4, CONST_BITS - PASS1_BITS);
    }
    for (c = 0; c < 8; c++) {
        i32 *dp = ws + c;
        tmp0 = dp[0] + dp[56]; tmp7 = dp[0] - dp[56];
        tmp1 = dp[8] + dp[48]; tmp6 = dp[8] - dp[48];
        tmp2 = dp[16] + dp[40]; tmp5 = dp[16] - dp[40];
        tmp3 = dp[24] + dp[32]; tmp4 = dp[24] - dp[32];
        tmp10 = tmp0 + tmp3; tmp13 = tmp0 - tmp3;
        tmp11 = tmp1 + tmp2; tmp12 = tmp1 - tmp2;
        dp[0]  = DESCALE(tmp10 + tmp11, PASS1_BITS);
        dp[32] = DESCALE(tmp10 - tmp11, PASS1_BITS);
        z1 = (tmp12 + tmp13) * FIX_0_541196100;
        dp[16] = DESCALE(z1 + tmp13 * FIX_0_765366865, CONST_BITS + PASS1_BITS);
        dp[48] = DESCALE(z1 + tmp12 * (-FIX_1_847759065), CONST_BITS + PASS1_BITS);
        z1 = tmp4 + tmp7; z2 = tmp5 + tmp6; z3 = tmp4 + tmp6; z4 = tmp5 + tmp7;
        z5 = (z3 + z4) * FIX_1_175875602;
        tmp4 *= FIX_0_298631336; tmp5 *= FIX_2_053119869;
        tmp6 *= FIX_3_072711026; tmp7 *= FIX_1_501321110;
        z1 *= -FIX_0_899976223; z2 *= -FIX_2_562915447;
        z3 *= -FIX_1_961570560; z4 *= -FIX_0_390180644;
        z3 += z5; z4 += z5;
        dp[56] = DESCALE(tmp4 + z1 + z3, CONST_BITS + PASS1_BITS);
        dp[40] = DESCALE(tmp5 + z2 + z4, CONST_BITS + PASS1_BITS);
        dp[24] = DESCALE(tmp6 + z2 + z3, CONST_BITS + PASS1_BITS);
        dp[8]  = DESCALE(tmp7 + z1 + z4, CONST_BITS + PASS1_BITS);
    }
}

/* ========================================================================= */
/* DECODER                                                                   */
/* ========================================================================= */

struct hufftab {
    u16 lut[512];       /* 9-bit lookahead: (len<<8)|sym, 0 = longer/invalid  */
    i32 maxcode[18];    /* per length, -1 = none; [17] sentinel               */
    i32 valoff[17];     /* index = code + valoff[len]                          */
    u8  vals[256];
    u8  present;
};

struct dctx {
    struct hufftab dc[4], ac[4];
    i16 acf[2][512];    /* AC "fast" tables for table ids 0/1: one 9-bit peek gives (run, value,
                           total bits) = (value*256)|(run*16)|nbits, 0 = take the long path     */
    i32 qm[4][64];      /* dequantisation multipliers, natural order (islow: q, fast: q*AAN scale) */
    u8  qpresent[4];
    u8  comp_id[JPEG_MAX_COMP];
    u8  fast;           /* JPEG_XFORM_FAST selected                                             */
    u8  coef_mask;      /* bit i: component i is delivered as quantised coefficient blocks      */
    u8  qm_ready;       /* qm matches `fast` and the current quant tables                       */
};

typedef struct {
    const u8 *p, *end;
    u32 acc;
    int nb;             /* valid bits in acc (right aligned)                   */
    int zf;             /* fake zero bytes appended after marker/EOF           */
    jpeg_read_fn rd;    /* callback mode only                                  */
    void *rdctx;
    u8 *buf;            /* refill buffer                                       */
    u32 bufcap;
    int eof;            /* rd returned 0 or an error                           */
    int rderr;          /* rd returned < 0                                     */
} bits_t;

/* callback mode: keep the unread tail, append the next chunk behind it */
static void rd_refill(bits_t *b)
{
    u32 keep = (u32)(b->end - b->p), room, ask;
    long n;

    if (!b->rd || b->eof) return;
    if (keep && b->p != b->buf) memmove(b->buf, b->p, keep);
    b->p = b->buf;
    b->end = b->buf + keep;
    room = b->bufcap - keep;
    ask = room < (u32)JPEG_RD_BUF ? room : (u32)JPEG_RD_BUF;
    if (!ask) { b->eof = 1; return; }
    n = b->rd(b->rdctx, b->buf + keep, ask);
    if (n < 0) { b->rderr = 1; b->eof = 1; return; }
    if (n == 0) { b->eof = 1; return; }
    if ((u32)n > ask) n = (long)ask;
    b->end += n;
}

/* make n contiguous bytes available at b->p; 0 at end of data / read error / n too big */
static int rd_have(bits_t *b, u32 n)
{
    while ((u32)(b->end - b->p) < n) {
        if (!b->rd || b->eof || n > b->bufcap) return 0;
        rd_refill(b);
    }
    return 1;
}

static int rd_skip(bits_t *b, u32 n)
{
    while (n) {
        u32 avail;
        if (!rd_have(b, 1)) return 0;
        avail = (u32)(b->end - b->p);
        if (avail > n) avail = n;
        b->p += avail;
        n -= avail;
    }
    return 1;
}

/* next marker code (skips stuffed FF00, fill FFs, RSTn, TEM); -1 at end of data */
static int rd_next_marker(bits_t *b)
{
    for (;;) {
        int m;
        while (rd_have(b, 1) && *b->p != 0xFF) b->p++;
        if (!rd_have(b, 1)) return -1;
        while (rd_have(b, 1) && *b->p == 0xFF) b->p++;
        if (!rd_have(b, 1)) return -1;
        m = *b->p++;
        if (m == 0x00 || m == 0x01 || (m >= 0xD0 && m <= 0xD7)) continue;
        return m;
    }
}

static void bits_fill(bits_t *b)
{
    /* a fill consumes at most 8 bytes (4 x "FF 00") and peeks one more: keep 10 in the window */
    if (b->rd && (b->end - b->p) < 10) {
        while ((b->end - b->p) < 10 && !b->eof) rd_refill(b);
    }
    while (b->nb <= 24) {
        u32 v = 0;
        const u8 *p = b->p;
        if (p < b->end) {
            v = *p;
            if (v == 0xFF) {
                if (p + 1 < b->end && p[1] == 0x00) {
                    b->p = p + 2;                 /* stuffed 0xFF */
                } else {
                    v = 0; b->zf++;               /* marker: feed zeros, stay */
                }
            } else {
                b->p = p + 1;
            }
        } else {
            b->zf++;
        }
        b->acc = (b->acc << 8) | v;
        b->nb += 8;
    }
}

static int build_huff(struct hufftab *h, i16 *fast, const u8 *counts, const u8 *vals, int n)
{
    i32 code = 0;
    int l, i, k = 0;

    if (n > 256) return JPEG_ERR_FORMAT;
    memset(h->lut, 0, sizeof h->lut);
    memcpy(h->vals, vals, (sw_size)n);
    for (l = 1; l <= 16; l++) {
        h->valoff[l] = k - code;
        for (i = 0; i < counts[l - 1]; i++) {
            if (l <= 9) {
                i32 base = code << (9 - l), fill = 1 << (9 - l), j;
                if (base + fill > 512) return JPEG_ERR_FORMAT;
                for (j = 0; j < fill; j++) h->lut[base + j] = (u16)((l << 8) | vals[k]);
            }
            code++; k++;
        }
        if (code > (1 << l)) return JPEG_ERR_FORMAT;         /* oversubscribed */
        h->maxcode[l] = counts[l - 1] ? code - 1 : -1;
        code <<= 1;
    }
    h->maxcode[0] = -1;
    h->maxcode[17] = 0x7FFFFFFF;
    h->present = 1;
    if (fast) {                                            /* combined (run, value, length) lookup */
        int idx;
        memset(fast, 0, 512 * sizeof(i16));
        for (idx = 0; idx < 512; idx++) {
            u32 e = h->lut[idx];
            int l = (int)(e >> 8), sym = (int)(e & 255), sz = sym & 15, m, v;
            if (!e || !sz || l + sz > 9) continue;
            m = (idx >> (9 - l - sz)) & ((1 << sz) - 1);
            v = (m < (1 << (sz - 1))) ? m - (1 << sz) + 1 : m;
            if (v < -128 || v > 127) continue;
            fast[idx] = (i16)(v * 256 + ((sym >> 4) << 4) + (l + sz));
        }
    }
    return JPEG_OK;
}

static int huff_decode_slow(bits_t *b, const struct hufftab *h)
{
    int l = 10;
    i32 code = (i32)((b->acc >> (b->nb - 10)) & 0x3FF);
    while (l <= 16 && code > h->maxcode[l]) {
        l++;
        if (l > 16) break;
        code = (i32)((b->acc >> (b->nb - l)) & ((1u << l) - 1u));
    }
    if (l > 16) return -1;
    b->nb -= l;
    return h->vals[(code + h->valoff[l]) & 255];
}

/* Decode one block. Two output forms (qz == NULL selects the first, resolved at compile time):
 *  - pixel form: blk[] (natural order, ALREADY DEQUANTISED with qm; must be all-zero on entry);
 *    nzl[0..*nnz-1] lists the natural indices of the nonzero AC coefficients so the caller can
 *    clear exactly those afterwards.
 *  - coefficient form: qz[0..63] = the QUANTISED coefficients in zigzag order (cleared here).
 * Returns the highest nonzero zigzag index (0 = DC only) or a negative error. */
SW_INLINE int decode_block(bits_t *b, const struct hufftab *dct, const struct hufftab *act, const i16 *acf,
                           i32 *pred, i32 *blk, const i32 *qm, u8 *nzl, int *nnz, i16 *qz)
{
    /* The bit-reader state lives in locals (registers) inside the block: stores to blk[]/nzl[] can
     * alias the bits_t fields, which would force a reload after every coefficient. It is written
     * back before anything that reads b->acc/b->nb (refill, long codes) and before returning. */
    u32 acc = b->acc;
    int nb = b->nb;
    int s, k, rs, nat, maxk = 0, n = 0;
#define SYNC_OUT() do { b->acc = acc; b->nb = nb; } while (0)
#define SYNC_IN()  do { acc = b->acc; nb = b->nb; } while (0)
#define FILL()     do { SYNC_OUT(); bits_fill(b); SYNC_IN(); } while (0)
#define HUFF(h, sym) do { \
        u32 e_ = (h)->lut[(acc >> (nb - 9)) & 511]; \
        if (e_) { nb -= (int)(e_ >> 8); sym = (int)(e_ & 255); } \
        else { SYNC_OUT(); sym = huff_decode_slow(b, (h)); SYNC_IN(); } \
    } while (0)
#define RECV(sz, val) do { \
        i32 v_; \
        nb -= (sz); \
        v_ = (i32)((acc >> nb) & ((1u << (sz)) - 1u)); \
        if (v_ < (1 << ((sz) - 1))) v_ -= (1 << (sz)) - 1; \
        val = v_; \
    } while (0)

    if (nb < 16) FILL();
    HUFF(dct, s);
    if (s < 0 || s > 15) { SYNC_OUT(); return JPEG_ERR_DATA; }
    if (s) {
        i32 dv;
        if (nb < s) FILL();
        RECV(s, dv);
        *pred += dv;
    }
    if (qz) { memset(qz, 0, 128); qz[0] = (i16)*pred; }
    else blk[0] = ((i32)(i16)*pred * qm[0]) >> QSH;

    k = 1;
    while (k < 64) {
        if (nb < 16) FILL();
        if (acf) {
            i32 f = acf[(acc >> (nb - 9)) & 511];
            if (f) {                                       /* short code + short amplitude: one lookup */
                nb -= f & 15;
                k += (f >> 4) & 15;
                if (k > 63) { SYNC_OUT(); return JPEG_ERR_DATA; }
                if (qz) {
                    qz[k] = (i16)(f >> 8);
                } else {
                    nat = zz[k];
                    blk[nat] = ((f >> 8) * qm[nat]) >> QSH;
                    nzl[n++] = (u8)nat;
                }
                maxk = k;
                k++;
                continue;
            }
        }
        HUFF(act, rs);
        if (rs < 0) { SYNC_OUT(); return JPEG_ERR_DATA; }
        s = rs & 15;
        if (s == 0) {
            if ((rs >> 4) == 15) { k += 16; continue; }
            break;
        }
        k += rs >> 4;
        if (k > 63) { SYNC_OUT(); return JPEG_ERR_DATA; }
        {
            i32 cv;
            if (nb < s) FILL();
            RECV(s, cv);
            if (qz) {
                qz[k] = (i16)cv;
            } else {
                nat = zz[k];
                blk[nat] = ((i32)(i16)cv * qm[nat]) >> QSH;
                nzl[n++] = (u8)nat;
            }
        }
        maxk = k;
        k++;
    }
    SYNC_OUT();
    *nnz = n;
    return maxk;
#undef RECV
#undef HUFF
#undef FILL
#undef SYNC_IN
#undef SYNC_OUT
}

static int do_restart(bits_t *b)
{
    if (b->zf * 8 > b->nb) return JPEG_ERR_TRUNC;     /* consumed fake bits */
    for (;;) {
        const u8 *p;
        if (!rd_have(b, 2)) return b->rderr ? JPEG_ERR_IO : JPEG_ERR_TRUNC;
        p = b->p;
        if (!(p[0] == 0xFF && p[1] != 0x00 && p[1] != 0xFF)) { b->p = p + 1; continue; }
        if (p[1] >= 0xD0 && p[1] <= 0xD7) { b->p = p + 2; break; }
        return JPEG_ERR_DATA;                         /* other marker too early */
    }
    b->acc = 0; b->nb = 0; b->zf = 0;
    return JPEG_OK;
}

/* Per-scan decoding state. The whole-frame decoder and the streaming decoder share
 * decode_mcu_row(); the streaming API keeps this struct alive between bands. */
struct scanst {
    bits_t b;
    i32 pred[JPEG_MAX_COMP];     /* DC predictors, indexed by FRAME component */
    int cnt;                     /* MCUs decoded since the last restart marker */
    int ns, cidx[JPEG_MAX_COMP]; /* scan components -> frame component index */
    u8 dcs[JPEG_MAX_COMP], acs[JPEG_MAX_COMP];
    u32 mcus_x, mcus_y;
};

/* Decode ONE MCU row (the unit of the streaming API).
 * base[i] / stride[i]: top-left sample and row pitch of the MCU row of scan component i (a band
 * of 8*v rows, or 8 rows for a single-component scan). */
static int decode_mcu_row(struct dctx *c, const jpeg_image *img, struct scanst *s,
                          u8 *const base[JPEG_MAX_COMP], const int stride[JPEG_MAX_COMP])
{
    i32 blk[64];
    u8 nzl[64];
    u32 mx;
    int ri = img->restart_interval, ns = s->ns, i, j, bx, by, rc, fast = c->fast;

    memset(blk, 0, sizeof blk);
    for (mx = 0; mx < s->mcus_x; mx++) {
        if (ri) {
            if (s->cnt == ri) {
                rc = do_restart(&s->b);
                if (rc) return rc;
                s->pred[0] = s->pred[1] = s->pred[2] = 0;
                s->cnt = 0;
            }
            s->cnt++;
        }
        for (i = 0; i < ns; i++) {
            const jpeg_comp *cp = &img->comp[s->cidx[i]];
            const struct hufftab *dct = &c->dc[s->dcs[i]], *act = &c->ac[s->acs[i]];
            const i16 *acf = s->acs[i] < 2 ? c->acf[s->acs[i]] : 0;
            const i32 *qm = c->qm[cp->tq];
            int nh = (ns == 1) ? 1 : cp->h, nv = (ns == 1) ? 1 : cp->v, st = stride[i];
            int coef = (c->coef_mask >> s->cidx[i]) & 1;
            for (by = 0; by < nv; by++) {
                for (bx = 0; bx < nh; bx++) {
                    u8 *dst;
                    int nnz = 0, maxk;
                    if (coef) {                            /* quantised coefficients: st = bytes per block row */
                        i16 *qz = (i16 *)(void *)(base[i] + (sw_size)((u32)by * (u32)st)
                                                          + (sw_size)((mx * (u32)nh + (u32)bx) * 128u));
                        maxk = decode_block(&s->b, dct, act, acf, &s->pred[s->cidx[i]], blk, qm, nzl, &nnz, qz);
                        if (maxk < 0) return maxk;
                        continue;
                    }
                    dst = base[i] + (sw_size)((u32)by * 8u) * (u32)st
                                  + (mx * (u32)nh + (u32)bx) * 8u;
                    maxk = decode_block(&s->b, dct, act, acf, &s->pred[s->cidx[i]], blk, qm, nzl, &nnz, 0);
                    if (maxk < 0) return maxk;
                    if (maxk == 0) {                       /* DC only: the whole block is one value */
                        u8 v = fast ? clamp8(((blk[0] + (1 << (AAN_FB + 2))) >> (AAN_FB + 3)) + 128)
                                    : clamp8(((blk[0] + 4) >> 3) + 128);
                        int r;
                        for (r = 0; r < 8; r++, dst += st) {
                            dst[0] = dst[1] = dst[2] = dst[3] = v;
                            dst[4] = dst[5] = dst[6] = dst[7] = v;
                        }
                    } else {                               /* IDCT restricted to the occupied corner */
                        int sel = (zz_rowhi[maxk] > 3 ? 2 : 0) | (zz_colhi[maxk] > 3 ? 1 : 0);
                        if (fast) {
                            if (sel == 0) idct_aan_44(blk, dst, st);
                            else if (sel == 1) idct_aan_48(blk, dst, st);
                            else if (sel == 2) idct_aan_84(blk, dst, st);
                            else idct_aan_88(blk, dst, st);
                        } else {
                            if (sel == 0) idct_islow_44(blk, dst, st);
                            else if (sel == 1) idct_islow_48(blk, dst, st);
                            else if (sel == 2) idct_islow_84(blk, dst, st);
                            else idct_islow_88(blk, dst, st);
                        }
                        for (j = 0; j < nnz; j++) blk[nzl[j]] = 0;
                    }
                }
            }
        }
    }
    return JPEG_OK;
}

/* ---- marker parsing ---- */

/* Find next marker at or after p. Returns pointer to the byte AFTER the marker
 * code, *m = code; NULL if none. Skips stuffed FF00, fill FFs and RSTn/TEM. */
static const u8 *next_marker(const u8 *p, const u8 *end, int *m)
{
    for (;;) {
        while (p < end && *p != 0xFF) p++;
        while (p < end && *p == 0xFF) p++;
        if (p >= end) return 0;
        if (*p == 0x00 || *p == 0x01 || (*p >= 0xD0 && *p <= 0xD7)) { p++; continue; }
        *m = *p;
        return p + 1;
    }
}

static int parse_sof(const u8 *seg, u32 len, jpeg_image *img)
{
    u32 prec, w, h, n, i, mcus_x, mcus_y;
    int hmax = 1, vmax = 1;

    if (len < 6) return JPEG_ERR_FORMAT;
    prec = seg[0];
    h = ((u32)seg[1] << 8) | seg[2];
    w = ((u32)seg[3] << 8) | seg[4];
    n = seg[5];
    if (prec != 8) return JPEG_ERR_UNSUPPORTED;
    if (w == 0 || h == 0) return JPEG_ERR_UNSUPPORTED;      /* DNL */
    if (n != 1 && n != 3) return JPEG_ERR_UNSUPPORTED;
    if (len < 6 + 3 * n) return JPEG_ERR_FORMAT;

    memset(img, 0, sizeof *img);
    img->width = (int)w; img->height = (int)h; img->ncomp = (int)n;
    for (i = 0; i < n; i++) {
        jpeg_comp *cp = &img->comp[i];
        int hh = seg[7 + 3 * i] >> 4, vv = seg[7 + 3 * i] & 15;
        /* component id (seg[6+3i]) is re-read from the SOF when SOS selects */
        if (n == 1) { hh = 1; vv = 1; }
        if (hh < 1 || hh > 4 || vv < 1 || vv > 4) return JPEG_ERR_UNSUPPORTED;
        if (seg[8 + 3 * i] > 3) return JPEG_ERR_FORMAT;
        cp->h = hh; cp->v = vv; cp->tq = seg[8 + 3 * i];
        if (hh > hmax) hmax = hh;
        if (vv > vmax) vmax = vv;
    }
    for (i = 0; i < n; i++) {
        int rh = hmax, rv = vmax;                  /* hmax % h, vmax % v without a divide */
        while (rh >= img->comp[i].h) rh -= img->comp[i].h;
        while (rv >= img->comp[i].v) rv -= img->comp[i].v;
        if (rh || rv) return JPEG_ERR_UNSUPPORTED;
    }
    img->hmax = hmax; img->vmax = vmax;
    mcus_x = cdiv(w, 8u * (u32)hmax);
    mcus_y = cdiv(h, 8u * (u32)vmax);
    for (i = 0; i < n; i++) {
        jpeg_comp *cp = &img->comp[i];
        cp->pw = (int)(mcus_x * (u32)cp->h * 8u);
        cp->ph = (int)(mcus_y * (u32)cp->v * 8u);
        cp->stride = cp->pw;
        cp->width = (int)cdiv(w * (u32)cp->h, (u32)hmax);
        cp->height = (int)cdiv(h * (u32)cp->v, (u32)vmax);
    }
    return JPEG_OK;
}

/* total arena bytes for the frame (planes laid out after the context) */
static int frame_layout(const jpeg_image *img, u32 *off, u32 *total)
{
    u64 pos = align32((u32)sizeof(struct dctx));
    int i;
    for (i = 0; i < img->ncomp; i++) {
        u64 sz = (u64)(u32)img->comp[i].stride * (u32)img->comp[i].ph;
        off[i] = (u32)pos;
        pos = (pos + sz + 31u) & ~(u64)31u;
        if (pos > 0xFFFFFF00u) return JPEG_ERR_ARENA;
    }
    *total = (u32)pos;
    return JPEG_OK;
}

static int find_sof(const u8 *in, unsigned long inlen, jpeg_image *img)
{
    const u8 *p, *end = in + inlen;
    int m;
    if (!in || inlen < 4 || in[0] != 0xFF || in[1] != 0xD8) return JPEG_ERR_FORMAT;
    p = in + 2;
    while ((p = next_marker(p, end, &m)) != 0) {
        u32 len;
        if (m == 0xD8) continue;
        if (m == 0xD9 || m == 0xDA) return JPEG_ERR_FORMAT;         /* no frame header */
        if (p + 2 > end) return JPEG_ERR_TRUNC;
        len = ((u32)p[0] << 8) | p[1];
        if (len < 2 || p + len > end) return JPEG_ERR_TRUNC;
        if (m == 0xC0 || m == 0xC1) return parse_sof(p + 2, len - 2, img);
        if ((m >= 0xC2 && m <= 0xCF && m != 0xC4 && m != 0xC8 && m != 0xCC))
            return JPEG_ERR_UNSUPPORTED;                             /* progressive/lossless/arith */
        p += len;
    }
    return JPEG_ERR_FORMAT;
}

unsigned long jpeg_decode_arena_size(const unsigned char *in, unsigned long inlen)
{
    jpeg_image img;
    u32 off[JPEG_MAX_COMP], total;
    if (find_sof(in, inlen, &img) != JPEG_OK) return 0;
    if (frame_layout(&img, off, &total) != JPEG_OK) return 0;
    return (unsigned long)total + 32u;      /* + base alignment slack */
}

/* Dequantisation multipliers in natural order, QSH (=5) extra fractional bits: islow uses q, the
 * fast mode folds the AAN scale factors in (Q10 before the final >> QSH => Q5 coefficients). Rebuilt whenever the mode or the quant tables change. */
static void build_qm(struct dctx *c, const jpeg_image *img)
{
    int t, k;
    for (t = 0; t < 4; t++) {
        if (!c->qpresent[t]) continue;
        for (k = 0; k < 64; k++) {
            u32 q = img->qt[t][k];
            int nat = zz[k];
            if (!c->fast) c->qm[t][nat] = (i32)(q << QSH);              /* (c*q*32)>>5 == c*q: exact */
            else c->qm[t][nat] = (i32)(((u64)(q * aan14[nat >> 3]) * aan14[nat & 7] + (1u << 17)) >> 18);   /* q*a_i*a_j in Q10 */
        }
    }
    c->qm_ready = 1;
}

/* Parse the SOS payload: component selectors, Huffman tables, MCU geometry.
 * Resets DC predictors and the restart counter. */
static int scan_setup(struct dctx *c, const jpeg_image *img, struct scanst *s, const u8 *seg, u32 len)
{
    int ns, j, t;

    if (len < 1) return JPEG_ERR_FORMAT;
    ns = seg[0];
    if (ns < 1 || ns > img->ncomp || len < (u32)(1 + 2 * ns + 3)) return JPEG_ERR_FORMAT;
    for (j = 0; j < ns; j++) {
        int cid = seg[1 + 2 * j], found = -1;
        for (t = 0; t < img->ncomp; t++) if (c->comp_id[t] == cid) found = t;
        if (found < 0) return JPEG_ERR_FORMAT;
        for (t = 0; t < j; t++) if (s->cidx[t] == found) return JPEG_ERR_FORMAT;   /* component listed twice */
        s->cidx[j] = found;
        s->dcs[j] = seg[2 + 2 * j] >> 4; s->acs[j] = seg[2 + 2 * j] & 15;
        if (s->dcs[j] > 3 || s->acs[j] > 3) return JPEG_ERR_FORMAT;
        if (!c->dc[s->dcs[j]].present || !c->ac[s->acs[j]].present) return JPEG_ERR_FORMAT;
        if (!c->qpresent[img->comp[found].tq]) return JPEG_ERR_FORMAT;
    }
    s->ns = ns;
    if (ns == 1) {
        const jpeg_comp *cp = &img->comp[s->cidx[0]];
        s->mcus_x = cdiv((u32)cp->width, 8);
        s->mcus_y = cdiv((u32)cp->height, 8);
    } else {
        s->mcus_x = cdiv((u32)img->width, 8u * (u32)img->hmax);
        s->mcus_y = cdiv((u32)img->height, 8u * (u32)img->vmax);
    }
    s->pred[0] = s->pred[1] = s->pred[2] = 0;
    s->cnt = 0;
    return JPEG_OK;
}

/* Parse markers up to and including the next SOS header (DQT/DHT/SOF/DRI are consumed on
 * the way, APPn/COM/... skipped without needing them in memory).
 * Returns 1: SOS found (*sos, *soslen = its payload, valid until the next reader refill);
 *             r->p = first entropy-coded byte
 *         0: EOI (or end of data) reached
 *        <0: error */
static int parse_to_sos(struct dctx *c, jpeg_image *out, int *have_sof, bits_t *r,
                        const u8 **sos, u32 *soslen)
{
    int m, rc;

    while ((m = rd_next_marker(r)) >= 0) {
        u32 len;
        const u8 *seg;
        if (m == 0xD8) continue;
        if (m == 0xD9) break;                              /* first EOI: done */
        if (m >= 0xC2 && m <= 0xCF && m != 0xC4 && m != 0xC8 && m != 0xCC)
            return JPEG_ERR_UNSUPPORTED;                   /* progressive / lossless / arithmetic */
        if (!rd_have(r, 2)) return r->rderr ? JPEG_ERR_IO : JPEG_ERR_TRUNC;
        len = ((u32)r->p[0] << 8) | r->p[1];
        if (len < 2) return JPEG_ERR_TRUNC;
        if (m != 0xDB && m != 0xC4 && m != 0xC0 && m != 0xC1 && m != 0xDD && m != 0xDA) {
            if (!rd_skip(r, len)) return r->rderr ? JPEG_ERR_IO : JPEG_ERR_TRUNC;   /* APPn, COM, ... */
            continue;
        }
        if (!rd_have(r, len)) {
            if (r->rderr) return JPEG_ERR_IO;
            return (r->rd && len > r->bufcap) ? JPEG_ERR_UNSUPPORTED : JPEG_ERR_TRUNC;
        }
        seg = r->p + 2; len -= 2;

        if (m == 0xDB) {                                   /* DQT */
            u32 pos = 0;
            while (pos < len) {
                u32 pq = seg[pos] >> 4, tq = seg[pos] & 15, k;
                pos++;
                if (tq > 3 || pq > 1) return JPEG_ERR_FORMAT;
                if (pos + 64 * (pq + 1) > len) return JPEG_ERR_FORMAT;
                for (k = 0; k < 64; k++) {
                    if (pq) { out->qt[tq][k] = (u16)(((u32)seg[pos] << 8) | seg[pos + 1]); pos += 2; }
                    else    { out->qt[tq][k] = seg[pos++]; }
                }
                c->qpresent[tq] = 1;
            }
        } else if (m == 0xC4) {                            /* DHT */
            u32 pos = 0;
            while (pos < len) {
                u32 tc = seg[pos] >> 4, th = seg[pos] & 15, n = 0, k;
                if (pos + 17 > len || tc > 1 || th > 3) return JPEG_ERR_FORMAT;
                for (k = 0; k < 16; k++) n += seg[pos + 1 + k];
                if (n > 256 || pos + 17 + n > len) return JPEG_ERR_FORMAT;
                rc = build_huff(tc ? &c->ac[th] : &c->dc[th], (tc && th < 2) ? c->acf[th] : 0,
                                seg + pos + 1, seg + pos + 17, (int)n);
                if (rc) return rc;
                pos += 17 + n;
            }
        } else if (m == 0xC0 || m == 0xC1) {               /* SOF0 / SOF1(8-bit) */
            jpeg_image tmp;
            int j;
            if (*have_sof) return JPEG_ERR_FORMAT;
            rc = parse_sof(seg, len, &tmp);
            if (rc) return rc;
            for (j = 0; j < tmp.ncomp; j++) {
                out->comp[j] = tmp.comp[j];
                c->comp_id[j] = seg[6 + 3 * j];
            }
            out->width = tmp.width; out->height = tmp.height; out->ncomp = tmp.ncomp;
            out->hmax = tmp.hmax; out->vmax = tmp.vmax;
            *have_sof = 1;
        } else if (m == 0xDD) {                            /* DRI */
            if (len < 2) return JPEG_ERR_FORMAT;
            out->restart_interval = (int)(((u32)seg[0] << 8) | seg[1]);
        } else {                                           /* SOS */
            if (!*have_sof) return JPEG_ERR_FORMAT;
            *sos = seg; *soslen = len;
            r->p += len + 2;
            return 1;
        }
        r->p += len + 2;
    }
    return r->rderr ? JPEG_ERR_IO : 0;
}

int jpeg_decode(const unsigned char *in, unsigned long inlen,
                void *arena, unsigned long arenalen, jpeg_image *out)
{
    const u8 *end = in + inlen, *seg;
    u8 *base;
    struct dctx *c;
    struct scanst s;
    u32 off[JPEG_MAX_COMP], total, slen, my;
    int rc, have_sof = 0, planes_ready = 0, comp_done = 0, ncd, i;

    if (!in || !arena || !out || inlen < 4) return JPEG_ERR_ARG;
    if (in[0] != 0xFF || in[1] != 0xD8) return JPEG_ERR_FORMAT;

    base = (u8 *)(((unsigned long)arena + 31u) & ~31ul);
    if ((unsigned long)(base - (u8 *)arena) > arenalen) return JPEG_ERR_ARENA;
    arenalen -= (unsigned long)(base - (u8 *)arena);
    if (arenalen < sizeof(struct dctx)) return JPEG_ERR_ARENA;
    c = (struct dctx *)(void *)base;
    memset(c, 0, sizeof *c);
    c->fast = SWJPEG_DEFAULT_XFORM;
    memset(out, 0, sizeof *out);
    memset(&s, 0, sizeof s);
    s.b.p = in + 2; s.b.end = end;                         /* memory-mode reader */

    for (;;) {
        rc = parse_to_sos(c, out, &have_sof, &s.b, &seg, &slen);
        if (rc < 0) return rc;
        if (rc == 0) break;
        if (!planes_ready) {                               /* planes live in the arena after the context */
            rc = frame_layout(out, off, &total);
            if (rc) return rc;
            if (arenalen < total) return JPEG_ERR_ARENA;
            for (i = 0; i < out->ncomp; i++) out->comp[i].data = base + off[i];
            planes_ready = 1;
        }
        rc = scan_setup(c, out, &s, seg, slen);
        if (rc) return rc;
        build_qm(c, out);
        s.b.acc = 0; s.b.nb = 0; s.b.zf = 0;
        for (my = 0; my < s.mcus_y; my++) {
            u8 *bp[JPEG_MAX_COMP];
            int st[JPEG_MAX_COMP];
            for (i = 0; i < s.ns; i++) {
                const jpeg_comp *cp = &out->comp[s.cidx[i]];
                u32 nv = (s.ns == 1) ? 1u : (u32)cp->v;
                bp[i] = cp->data + (sw_size)(my * nv * 8u) * (u32)cp->stride;
                st[i] = cp->stride;
            }
            rc = decode_mcu_row(c, out, &s, bp, st);
            if (rc) return rc;
        }
        if (s.b.zf * 8 > s.b.nb) return JPEG_ERR_TRUNC;
        for (i = 0; i < s.ns; i++) comp_done |= 1 << s.cidx[i];
    }
    if (!have_sof) return JPEG_ERR_FORMAT;
    ncd = 0;
    for (i = 0; i < out->ncomp; i++) ncd += (comp_done >> i) & 1;
    if (ncd != out->ncomp) return JPEG_ERR_TRUNC;
    return JPEG_OK;
}

/* ========================================================================= */
/* STREAMING DECODER: one MCU row ("band") per call, O(width) memory         */
/* ========================================================================= */

struct sdctx {
    struct dctx d;
    struct scanst s;
    jpeg_image meta;                 /* frame description (data pointers NULL) */
    u8 *band[JPEG_MAX_COMP];         /* one MCU-row band buffer per component  */
    u32 my;                          /* next MCU row to decode                 */
    int err;                         /* sticky error                           */
};

/* callback mode: refill buffer = one read chunk + 16 bytes of carry-over room */
#define SDEC_RDBUF ((u32)JPEG_RD_BUF + 16u)

/* band buffers laid out from offset `start`: component i gets stride * (8*v) bytes */
static int band_layout(const jpeg_image *img, u32 *off, u32 *total, u32 start, u32 coef_mask)
{
    u64 pos = start;
    int i;
    for (i = 0; i < img->ncomp; i++) {
        u64 sz = (u64)(u32)img->comp[i].stride * (8u * (u32)img->comp[i].v);
        if ((coef_mask >> i) & 1) sz *= 2;                 /* 64 x int16 per block instead of 64 bytes */
        off[i] = (u32)pos;
        pos = (pos + sz + 31u) & ~(u64)31u;
        if (pos > 0xFFFFFF00u) return JPEG_ERR_ARENA;
    }
    *total = (u32)pos;
    return JPEG_OK;
}

static unsigned long sdec_scratch_size_impl(const unsigned char *in, unsigned long inlen, unsigned opts)
{
    jpeg_image img;
    u32 off[JPEG_MAX_COMP], total;
    if (find_sof(in, inlen, &img) != JPEG_OK) return 0;
    if (band_layout(&img, off, &total, align32((u32)sizeof(struct sdctx)),
                    opts & ((1u << img.ncomp) - 1u)) != JPEG_OK) return 0;
    return (unsigned long)total + 32u;
}

unsigned long jpeg_sdec_scratch_size_ex(const unsigned char *in, unsigned long inlen, unsigned opts)
{
    return sdec_scratch_size_impl(in, inlen, opts);
}

unsigned long jpeg_sdec_scratch_size(const unsigned char *in, unsigned long inlen)
{
    return sdec_scratch_size_impl(in, inlen, 0);
}

unsigned long jpeg_sdec_cb_min_scratch(void)
{
    return (unsigned long)align32((u32)sizeof(struct sdctx)) + align32(SDEC_RDBUF) + 32u;
}

static unsigned long sdec_cb_scratch_size_impl(const jpeg_image *meta, unsigned opts)
{
    u32 off[JPEG_MAX_COMP], total;
    if (!meta || meta->ncomp < 1 || meta->ncomp > JPEG_MAX_COMP) return 0;
    if (band_layout(meta, off, &total, align32((u32)sizeof(struct sdctx)) + align32(SDEC_RDBUF),
                    opts & ((1u << meta->ncomp) - 1u)) != JPEG_OK) return 0;
    return (unsigned long)total + 32u;
}

unsigned long jpeg_sdec_cb_scratch_size_ex(const jpeg_image *meta, unsigned opts)
{
    return sdec_cb_scratch_size_impl(meta, opts);
}

unsigned long jpeg_sdec_cb_scratch_size(const jpeg_image *meta)
{
    return sdec_cb_scratch_size_impl(meta, 0);
}

/* in != NULL: memory mode.  rd != NULL: callback mode. */
static int sdec_init_common(const u8 *in, unsigned long inlen, jpeg_read_fn rd, void *rdctx,
                            void *scratch, unsigned long slen, unsigned opts, jpeg_sdec *d, jpeg_image *meta)
{
    const u8 *seg;
    u8 *base;
    struct sdctx *c;
    u32 off[JPEG_MAX_COMP], total, soslen, pre;
    int rc, have_sof = 0, i;

    base = (u8 *)(((unsigned long)scratch + 31u) & ~31ul);
    if ((unsigned long)(base - (u8 *)scratch) > slen) return JPEG_ERR_ARENA;
    slen -= (unsigned long)(base - (u8 *)scratch);
    pre = align32((u32)sizeof(struct sdctx)) + (rd ? align32(SDEC_RDBUF) : 0u);
    if (slen < pre) return JPEG_ERR_ARENA;
    c = (struct sdctx *)(void *)base;
    memset(c, 0, sizeof *c);
    c->d.fast = SWJPEG_DEFAULT_XFORM;

    if (rd) {
        bits_t *b = &c->s.b;
        b->rd = rd; b->rdctx = rdctx;
        b->buf = base + align32((u32)sizeof(struct sdctx));
        b->bufcap = SDEC_RDBUF;
        b->p = b->end = b->buf;
        if (!rd_have(b, 2)) return b->rderr ? JPEG_ERR_IO : JPEG_ERR_FORMAT;
        if (b->p[0] != 0xFF || b->p[1] != 0xD8) return JPEG_ERR_FORMAT;
        b->p += 2;
    } else {
        c->s.b.p = in + 2; c->s.b.end = in + inlen;
    }

    rc = parse_to_sos(&c->d, &c->meta, &have_sof, &c->s.b, &seg, &soslen);
    if (rc < 0) return rc;
    if (rc == 0) return JPEG_ERR_FORMAT;                   /* no scan in the file */
    rc = scan_setup(&c->d, &c->meta, &c->s, seg, soslen);
    if (rc) return rc;
    /* a band holds one MCU row of EVERY component: only a single interleaved scan streams */
    if (c->s.ns != c->meta.ncomp) return JPEG_ERR_UNSUPPORTED;
    c->d.coef_mask = (u8)(opts & ((1u << c->meta.ncomp) - 1u));
    rc = band_layout(&c->meta, off, &total, pre, c->d.coef_mask);
    if (rc) return rc;

    *meta = c->meta;                                       /* qt, sampling, restart interval, full-frame dims */
    for (i = 0; i < JPEG_MAX_COMP; i++) meta->comp[i].data = 0;
    if (slen < total) return JPEG_ERR_ARENA;               /* meta is valid: size the scratch with jpeg_sdec_cb_scratch_size() */

    for (i = 0; i < c->meta.ncomp; i++) c->band[i] = base + off[i];
    c->s.b.acc = 0; c->s.b.nb = 0; c->s.b.zf = 0;
    c->my = 0; c->err = 0;
    d->ctx = c;
    return JPEG_OK;
}

static int sdec_init_impl(const unsigned char *in, unsigned long inlen, void *scratch, unsigned long slen,
                          unsigned opts, jpeg_sdec *d, jpeg_image *meta)
{
    if (!d) return JPEG_ERR_ARG;
    d->ctx = 0;
    if (!in || !scratch || !meta || inlen < 4) return JPEG_ERR_ARG;
    if (in[0] != 0xFF || in[1] != 0xD8) return JPEG_ERR_FORMAT;
    return sdec_init_common(in, inlen, 0, 0, scratch, slen, opts, d, meta);
}

int jpeg_sdec_init_ex(const unsigned char *in, unsigned long inlen, void *scratch, unsigned long slen,
                      unsigned opts, jpeg_sdec *d, jpeg_image *meta)
{
    return sdec_init_impl(in, inlen, scratch, slen, opts, d, meta);
}

int jpeg_sdec_init(const unsigned char *in, unsigned long inlen, void *scratch, unsigned long slen,
                   jpeg_sdec *d, jpeg_image *meta)
{
    return sdec_init_impl(in, inlen, scratch, slen, 0, d, meta);
}

static int sdec_init_cb_impl(jpeg_read_fn rd, void *rd_ctx, void *scratch, unsigned long slen,
                             unsigned opts, jpeg_sdec *d, jpeg_image *meta)
{
    if (!d) return JPEG_ERR_ARG;
    d->ctx = 0;
    if (!rd || !scratch || !meta) return JPEG_ERR_ARG;
    return sdec_init_common(0, 0, rd, rd_ctx, scratch, slen, opts, d, meta);
}

int jpeg_sdec_init_cb_ex(jpeg_read_fn rd, void *rd_ctx, void *scratch, unsigned long slen,
                         unsigned opts, jpeg_sdec *d, jpeg_image *meta)
{
    return sdec_init_cb_impl(rd, rd_ctx, scratch, slen, opts, d, meta);
}

int jpeg_sdec_init_cb(jpeg_read_fn rd, void *rd_ctx, void *scratch, unsigned long slen,
                      jpeg_sdec *d, jpeg_image *meta)
{
    return sdec_init_cb_impl(rd, rd_ctx, scratch, slen, 0, d, meta);
}

int jpeg_sdec_set_xform(jpeg_sdec *d, int mode)
{
    struct sdctx *c;
    if (!d || !d->ctx || (mode != JPEG_XFORM_ACCURATE && mode != JPEG_XFORM_FAST)) return JPEG_ERR_ARG;
    c = (struct sdctx *)d->ctx;
    if (c->my != 0) return JPEG_ERR_STATE;                 /* only before the first band */
    c->d.fast = (u8)(mode == JPEG_XFORM_FAST);
    c->d.qm_ready = 0;
    return JPEG_OK;
}

int jpeg_sdec_band(jpeg_sdec *d, jpeg_comp bands[JPEG_MAX_COMP])
{
    struct sdctx *c;
    u8 *bp[JPEG_MAX_COMP];
    int st[JPEG_MAX_COMP], i, rc;
    u32 y0l, rows;

    if (!d || !d->ctx || !bands) return JPEG_ERR_ARG;
    c = (struct sdctx *)d->ctx;
    if (c->err) return c->err;
    if (c->my >= c->s.mcus_y) return 0;                    /* EOF */

    for (i = 0; i < c->s.ns; i++) {
        bp[i] = c->band[c->s.cidx[i]];
        st[i] = c->meta.comp[c->s.cidx[i]].stride;
        if ((c->d.coef_mask >> c->s.cidx[i]) & 1) st[i] *= 16;     /* bytes per row of 8x8 blocks of int16 */
    }
    if (!c->d.qm_ready) build_qm(&c->d, &c->meta);
    rc = decode_mcu_row(&c->d, &c->meta, &c->s, bp, st);
    if (rc == 0 && c->s.b.zf * 8 > c->s.b.nb) rc = JPEG_ERR_TRUNC;
    if (c->s.b.rderr) rc = JPEG_ERR_IO;                    /* the read callback failed */
    if (rc) { c->err = rc; return rc; }

    memset(bands, 0, sizeof(jpeg_comp) * JPEG_MAX_COMP);
    for (i = 0; i < c->meta.ncomp; i++) {
        const jpeg_comp *m = &c->meta.comp[i];
        jpeg_comp *b = &bands[i];
        u32 y0 = c->my * 8u * (u32)m->v, left = (u32)m->height - y0, bh = 8u * (u32)m->v;
        b->data = c->band[i];
        b->coef = (c->d.coef_mask >> i) & 1;
        b->stride = b->coef ? m->stride * 16 : m->stride;
        b->width = m->width;
        b->height = (int)(left < bh ? left : bh);          /* visible rows in this band */
        b->pw = m->pw;
        b->ph = (int)bh;                                   /* allocated rows in this band */
        b->h = m->h; b->v = m->v; b->tq = m->tq;
        b->y0 = (int)y0;
    }
    y0l = c->my * 8u * (u32)c->meta.vmax;
    rows = (u32)c->meta.height - y0l;
    if (rows > 8u * (u32)c->meta.vmax) rows = 8u * (u32)c->meta.vmax;
    c->my++;
    return (int)rows;
}

/* ========================================================================= */
/* ENCODER (baseline, Annex K Huffman tables)                                */
/* ========================================================================= */

static const u8 std_dc_lum_bits[16] = { 0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0 };
static const u8 std_dc_chr_bits[16] = { 0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0 };
static const u8 std_dc_vals[12] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 };

static const u8 std_ac_lum_bits[16] = { 0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7d };
static const u8 std_ac_lum_vals[162] = {
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12,
    0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
    0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xa1, 0x08,
    0x23, 0x42, 0xb1, 0xc1, 0x15, 0x52, 0xd1, 0xf0,
    0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0a, 0x16,
    0x17, 0x18, 0x19, 0x1a, 0x25, 0x26, 0x27, 0x28,
    0x29, 0x2a, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
    0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
    0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
    0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
    0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
    0x7a, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
    0x8a, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
    0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
    0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6,
    0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3, 0xc4, 0xc5,
    0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2, 0xd3, 0xd4,
    0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xe1, 0xe2,
    0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea,
    0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
    0xf9, 0xfa
};

static const u8 std_ac_chr_bits[16] = { 0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 0x77 };
static const u8 std_ac_chr_vals[162] = {
    0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21,
    0x31, 0x06, 0x12, 0x41, 0x51, 0x07, 0x61, 0x71,
    0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91,
    0xa1, 0xb1, 0xc1, 0x09, 0x23, 0x33, 0x52, 0xf0,
    0x15, 0x62, 0x72, 0xd1, 0x0a, 0x16, 0x24, 0x34,
    0xe1, 0x25, 0xf1, 0x17, 0x18, 0x19, 0x1a, 0x26,
    0x27, 0x28, 0x29, 0x2a, 0x35, 0x36, 0x37, 0x38,
    0x39, 0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
    0x49, 0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58,
    0x59, 0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68,
    0x69, 0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78,
    0x79, 0x7a, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
    0x88, 0x89, 0x8a, 0x92, 0x93, 0x94, 0x95, 0x96,
    0x97, 0x98, 0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5,
    0xa6, 0xa7, 0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4,
    0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3,
    0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2,
    0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda,
    0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9,
    0xea, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
    0xf9, 0xfa
};

struct ectx {
    u32 dc_ent[2][12];   /* (size << 16) | code                                    */
    u32 ac_ent[2][256];
    u32 rec[4][64];      /* wide path (any q > 255): floor((2^32-1)/q), zigzag order */
    u32 qr[4][64];       /* exact path: floor(2^20/q)+1, natural order             */
    u16 qb[4][64];       /* exact path: 4*q, natural order                         */
    i32 qaan[4][64];     /* fast path: 2^32 / (q*256*a_i*a_j), natural order        */
};

/* Output writer. memory mode (wr == NULL): [buf, end) is the caller's whole output buffer,
 * running out sets ovf. callback mode: [buf, end) is a small buffer that is pushed through
 * wr() whenever it fills up and once more at the end. */
typedef struct {
    u8 *o, *end, *buf;
    u32 acc;
    int nb;
    int ovf;            /* output full / write failed (sticky)                 */
    int ioerr;          /* ovf was caused by the write callback                */
    jpeg_write_fn wr;
    void *wctx;
    u32 flushed;        /* bytes already handed to wr                          */
    sw_size lim;        /* fast path while (address of o) <= lim = end - 8 (a put emits <= 8 bytes) */
} bw_t;

/* buffer full: callback mode drains it, memory mode overflows. Returns nonzero on failure. */
static int bw_full(bw_t *w)
{
    u32 len, done = 0;
    if (!w->wr || w->ovf) { w->ovf = 1; return 1; }
    len = (u32)(w->o - w->buf);
    while (done < len) {
        long n = w->wr(w->wctx, w->buf + done, len - done);
        if (n <= 0) { w->ioerr = 1; w->ovf = 1; return 1; }       /* error or no progress */
        if ((u32)n > len - done) n = (long)(len - done);
        done += (u32)n;                                             /* short writes are retried */
    }
    w->flushed += len;
    w->o = w->buf;
    return 0;
}

SW_INLINE void bw_byte(bw_t *w, u32 v)
{
    if (w->o >= w->end && bw_full(w)) return;
    *w->o++ = (u8)v;
}

static inline int bw_status(const bw_t *w)
{
    return w->ovf ? (w->ioerr ? JPEG_ERR_IO : JPEG_ERR_OVERFLOW) : JPEG_OK;
}

SW_INLINE void bw_put16(bw_t *w, u32 v) { bw_byte(w, v >> 8); bw_byte(w, v & 255u); }

/* near the end of the buffer: checked per byte; callback mode drains the buffer first */
static void bw_put_slow(bw_t *w, u32 acc, int nb)
{
    if (w->wr && !w->ovf && (sw_size)w->o > w->lim) bw_full(w);
    while (nb >= 8) {
        u32 byte;
        nb -= 8;
        byte = (acc >> nb) & 0xFFu;
        bw_byte(w, byte);
        if (byte == 0xFF) bw_byte(w, 0);
    }
    w->acc = acc;
    w->nb = nb;
}

/* bits must already be masked to len bits; len in 1..25 */
SW_INLINE void bw_put(bw_t *w, u32 bits, int len)
{
    u32 acc = (w->acc << len) | bits;
    int nb = w->nb + len;
    if ((sw_size)w->o > w->lim) { bw_put_slow(w, acc, nb); return; }
    if (nb >= 8) {
        u8 *o = w->o;
        do {
            u32 byte;
            nb -= 8;
            byte = (acc >> nb) & 0xFFu;
            *o++ = (u8)byte;
            if (byte == 0xFF) *o++ = 0;                    /* byte stuffing */
        } while (nb >= 8);
        w->o = o;
    }
    w->acc = acc;
    w->nb = nb;
}

static void bw_flush(bw_t *w)
{
    if (w->nb) bw_put(w, (1u << (8 - w->nb)) - 1u, 8 - w->nb);       /* pad with 1 bits */
}

/* ent[sym] = (size << 16) | code */
static void build_enc(u32 *ent, const u8 *bits, const u8 *vals)
{
    u32 c = 0;
    int l, i, k = 0;
    for (l = 1; l <= 16; l++) {
        for (i = 0; i < bits[l - 1]; i++, k++, c++) ent[vals[k]] = ((u32)l << 16) | c;
        c <<= 1;
    }
}

/* ---- wide path: any quant value > 255 (16-bit DQT). Slow reference code, always exact. ---- */
SW_INLINE i32 quant(i32 F, u32 q, u32 rec)
{
    u32 a = (F < 0) ? (u32)(-F) : (u32)F;
    u32 m = (a + 4u * q) >> 3;
    u32 t = (u32)((((u64)m * rec) + m) >> 32);
    return (F < 0) ? -(i32)t : (i32)t;
}

/* amplitude bits of v for a category of nbits, merged with its Huffman code into one write */
SW_INLINE void bw_sym(bw_t *w, u32 ent, u32 amp, u32 nbits)
{
    u32 size = ent >> 16, code = ent & 0xFFFFu, mask = (1u << nbits) - 1u;
    if (size + nbits > 25) {                               /* 16-bit code + 10-bit amplitude: split */
        bw_put(w, code, (int)size);
        if (nbits) bw_put(w, amp & mask, (int)nbits);
    } else {
        bw_put(w, (code << nbits) | (amp & mask), (int)(size + nbits));
    }
}

/* Huffman-code one block of quantised coefficients qz[0..63] (zigzag order), qz 4-byte aligned.
 * The bit-writer state (acc/nb/o) lives in locals for the whole block and is written back at the
 * end; the rare near-end-of-buffer case goes through bw_put_slow with the state synced. */
typedef u32 __attribute__((may_alias)) u32a;

#define BWL_PUT(bits_, len_) do { \
        acc = (acc << (len_)) | (bits_); \
        nb += (len_); \
        if ((sw_size)o > lim) { w->o = o; bw_put_slow(w, acc, nb); acc = w->acc; nb = w->nb; o = w->o; } \
        else if (nb >= 8) { \
            do { \
                u32 by_; \
                nb -= 8; \
                by_ = (acc >> nb) & 0xFFu; \
                *o++ = (u8)by_; \
                if (by_ == 0xFF) *o++ = 0; \
            } while (nb >= 8); \
        } \
    } while (0)
#define BWL_SYM(ent_, amp_, nbits_) do { \
        u32 e_ = (ent_), n_ = (nbits_), sz_ = e_ >> 16, cd_ = e_ & 0xFFFFu, mk_ = (1u << n_) - 1u; \
        if (sz_ + n_ > 25) { BWL_PUT(cd_, (int)sz_); if (n_) BWL_PUT((amp_) & mk_, (int)n_); } \
        else BWL_PUT((cd_ << n_) | ((amp_) & mk_), (int)(sz_ + n_)); \
    } while (0)

static void huff_block(bw_t *w, const struct ectx *e, int ts, const i16 *qz, i32 *pred)
{
    const u32 *dce = e->dc_ent[ts], *ace = e->ac_ent[ts];
    i32 v = qz[0], diff = v - *pred, sg = diff >> 31;
    u32 nbits, a = (u32)((diff ^ sg) - sg);
    u32 acc = w->acc;
    int nb = w->nb, k, j, r = 0;
    u8 *o = w->o;
    const sw_size lim = w->lim;

    *pred = v;
    nbits = a ? 32u - (u32)__builtin_clz(a) : 0u;
    if (nbits > 11) nbits = 11;
    BWL_SYM(dce[nbits], (u32)(diff + sg), nbits);

#define AC_RANGE(var, from, to) \
    for (var = (from); var < (to); var++) { \
        v = qz[var]; \
        if (v == 0) { r++; continue; } \
        while (r > 15) { BWL_SYM(ace[0xF0], 0, 0); r -= 16; } \
        sg = v >> 31; \
        a = (u32)((v ^ sg) - sg); \
        nbits = 32u - (u32)__builtin_clz(a); \
        BWL_SYM(ace[((u32)r << 4) | nbits], (u32)(v + sg), nbits); \
        r = 0; \
    }
    AC_RANGE(j, 1, 2)
    for (k = 2; k < 62; k += 4) {                          /* groups of four, aligned on 4-byte words */
        const u32a *q4 = (const u32a *)(const void *)(qz + k);
        if ((q4[0] | q4[1]) == 0) { r += 4; continue; }    /* four zero coefficients at once */
        AC_RANGE(j, k, k + 4)
    }
    AC_RANGE(j, 62, 64)
#undef AC_RANGE
    if (qz[63] == 0) BWL_SYM(ace[0x00], 0, 0);             /* EOB unless the last coefficient is used */
    w->acc = acc; w->nb = nb; w->o = o;
}
#undef BWL_SYM
#undef BWL_PUT

/* Exact quantiser, unrolled: natural-order F -> zigzag-order qz. Bit-identical to quant() for
 * q <= 255 (m*r stays below 2^32, floor(m/q) = (m*r)>>20 holds for m*q < 2^20). */
static void quant_zz_exact(const i32 *ws, const u16 *qb, const u32 *qr, i16 *qz)
{
#define QEX(i, zp) do { \
        i32 F_ = ws[i]; i32 sg_ = F_ >> 31; u32 a_ = (u32)((F_ ^ sg_) - sg_); \
        u32 t_ = (((a_ + qb[i]) >> 3) * qr[i]) >> 20; \
        qz[zp] = (i16)((t_ ^ (u32)sg_) - (u32)sg_); \
    } while (0)
    QEX(0, 0);
    QEX(1, 1);
    QEX(2, 5);
    QEX(3, 6);
    QEX(4, 14);
    QEX(5, 15);
    QEX(6, 27);
    QEX(7, 28);
    QEX(8, 2);
    QEX(9, 4);
    QEX(10, 7);
    QEX(11, 13);
    QEX(12, 16);
    QEX(13, 26);
    QEX(14, 29);
    QEX(15, 42);
    QEX(16, 3);
    QEX(17, 8);
    QEX(18, 12);
    QEX(19, 17);
    QEX(20, 25);
    QEX(21, 30);
    QEX(22, 41);
    QEX(23, 43);
    QEX(24, 9);
    QEX(25, 11);
    QEX(26, 18);
    QEX(27, 24);
    QEX(28, 31);
    QEX(29, 40);
    QEX(30, 44);
    QEX(31, 53);
    QEX(32, 10);
    QEX(33, 19);
    QEX(34, 23);
    QEX(35, 32);
    QEX(36, 39);
    QEX(37, 45);
    QEX(38, 52);
    QEX(39, 54);
    QEX(40, 20);
    QEX(41, 22);
    QEX(42, 33);
    QEX(43, 38);
    QEX(44, 46);
    QEX(45, 51);
    QEX(46, 55);
    QEX(47, 60);
    QEX(48, 21);
    QEX(49, 34);
    QEX(50, 37);
    QEX(51, 47);
    QEX(52, 50);
    QEX(53, 56);
    QEX(54, 59);
    QEX(55, 61);
    QEX(56, 35);
    QEX(57, 36);
    QEX(58, 48);
    QEX(59, 49);
    QEX(60, 57);
    QEX(61, 58);
    QEX(62, 62);
    QEX(63, 63);
#undef QEX
}

/*
 * FAST transform mode, encoder side: AAN forward DCT fused with the quantiser. 5 multiplies per 1-D
 * pass; the AAN output scale (8*a_i*a_j*2^(IB-R1)) is folded into the reciprocal table qaan, so
 * quantisation is one 32x32->64 multiply per coefficient. Error vs the exact DCT: rms 0.01, max
 * 0.11 of a coefficient unit (before quantisation).
 */
#define AAN_IB 7
#define AAN_FR1 2
#define FMUL(v, c) (((v) * (c) + 2048) >> 12)
typedef long long i64;

#define AAN_FDCT_1D(d0, d1, d2, d3, d4, d5, d6, d7, o0, o1, o2, o3, o4, o5, o6, o7) do { \
    i32 t0 = (d0) + (d7), t7 = (d0) - (d7), t1 = (d1) + (d6), t6 = (d1) - (d6); \
    i32 t2 = (d2) + (d5), t5 = (d2) - (d5), t3 = (d3) + (d4), t4 = (d3) - (d4); \
    i32 t10 = t0 + t3, t13 = t0 - t3, t11 = t1 + t2, t12 = t1 - t2; \
    i32 z1, z2, z3, z4, z5, z11, z13; \
    o0 = t10 + t11; o4 = t10 - t11; \
    z1 = FMUL(t12 + t13, 2896); o2 = t13 + z1; o6 = t13 - z1; \
    t10 = t4 + t5; t11 = t5 + t6; t12 = t6 + t7; \
    z5 = FMUL(t10 - t12, 1567); z2 = FMUL(t10, 2217) + z5; z4 = FMUL(t12, 5352) + z5; z3 = FMUL(t11, 2896); \
    z11 = t7 + z3; z13 = t7 - z3; \
    o5 = z13 + z2; o3 = z13 - z2; o1 = z11 + z4; o7 = z11 - z4; \
} while (0)

static void fdct_aan_quant(const u8 *src, int stride, const i32 *R, i16 *qz)
{
    i32 w[64];
    int r;

    for (r = 0; r < 8; r++, src += stride) {
        i32 d0 = (i32)src[0] << AAN_IB, d1 = (i32)src[1] << AAN_IB, d2 = (i32)src[2] << AAN_IB, d3 = (i32)src[3] << AAN_IB;
        i32 d4 = (i32)src[4] << AAN_IB, d5 = (i32)src[5] << AAN_IB, d6 = (i32)src[6] << AAN_IB, d7 = (i32)src[7] << AAN_IB;
        i32 o0, o1, o2, o3, o4, o5, o6, o7;
        AAN_FDCT_1D(d0, d1, d2, d3, d4, d5, d6, d7, o0, o1, o2, o3, o4, o5, o6, o7);
        o0 -= 1024 << AAN_IB;                              /* level shift: 8 samples * 128 */
        w[r * 8 + 0] = o0 >> AAN_FR1; w[r * 8 + 1] = o1 >> AAN_FR1; w[r * 8 + 2] = o2 >> AAN_FR1; w[r * 8 + 3] = o3 >> AAN_FR1;
        w[r * 8 + 4] = o4 >> AAN_FR1; w[r * 8 + 5] = o5 >> AAN_FR1; w[r * 8 + 6] = o6 >> AAN_FR1; w[r * 8 + 7] = o7 >> AAN_FR1;
    }
#define QA(F, i, zp) qz[zp] = (i16)(((i64)(F) * R[i] + 0x80000000LL) >> 32)
#define FCOL(c, z0, z1, z2, z3, z4, z5, z6, z7) do { \
        i32 d0 = w[c], d1 = w[8 + c], d2 = w[16 + c], d3 = w[24 + c], d4 = w[32 + c], d5 = w[40 + c], d6 = w[48 + c], d7 = w[56 + c]; \
        i32 o0, o1, o2, o3, o4, o5, o6, o7; \
        AAN_FDCT_1D(d0, d1, d2, d3, d4, d5, d6, d7, o0, o1, o2, o3, o4, o5, o6, o7); \
        QA(o0, c, z0); QA(o1, 8 + c, z1); QA(o2, 16 + c, z2); QA(o3, 24 + c, z3); \
        QA(o4, 32 + c, z4); QA(o5, 40 + c, z5); QA(o6, 48 + c, z6); QA(o7, 56 + c, z7); \
    } while (0)
    FCOL(0, 0, 2, 3, 9, 10, 20, 21, 35);
    FCOL(1, 1, 4, 8, 11, 19, 22, 34, 36);
    FCOL(2, 5, 7, 12, 18, 23, 33, 37, 48);
    FCOL(3, 6, 13, 17, 24, 32, 38, 47, 49);
    FCOL(4, 14, 16, 25, 31, 39, 46, 50, 57);
    FCOL(5, 15, 26, 30, 40, 45, 51, 56, 58);
    FCOL(6, 27, 29, 41, 44, 52, 55, 59, 62);
    FCOL(7, 28, 42, 43, 53, 54, 60, 61, 63);
#undef FCOL
#undef QA
}

/* wide path: the original per-coefficient loop (any quant value, 16-bit tables) */
static void encode_block_wide(bw_t *w, const struct ectx *e, int ts, const u16 *qt, const u32 *rec,
                              const u8 *src, int stride, i32 *pred)
{
    i32 ws[64], v, diff;
    u32 a, nbits;
    int k, r, sym;
    const u32 *dce = e->dc_ent[ts], *ace = e->ac_ent[ts];

    fdct_block(src, stride, ws);

    v = quant(ws[0], qt[0], rec[0]);
    if (v > 2047) v = 2047; else if (v < -2047) v = -2047;
    diff = v - *pred;
    *pred = v;
    a = (diff < 0) ? (u32)(-diff) : (u32)diff;
    nbits = (u32)bitlen(a);
    if (nbits > 11) nbits = 11;
    bw_sym(w, dce[nbits], (u32)(diff < 0 ? diff - 1 : diff), nbits);

    r = 0;
    for (k = 1; k < 64; k++) {
        v = quant(ws[zz[k]], qt[k], rec[k]);
        if (v == 0) { r++; continue; }
        if (v > 1023) v = 1023; else if (v < -1023) v = -1023;
        while (r > 15) { bw_sym(w, ace[0xF0], 0, 0); r -= 16; }
        a = (v < 0) ? (u32)(-v) : (u32)v;
        nbits = (u32)bitlen(a);
        sym = (r << 4) | (int)nbits;
        bw_sym(w, ace[sym], (u32)(v < 0 ? v - 1 : v), nbits);
        r = 0;
    }
    if (r) bw_sym(w, ace[0x00], 0, 0);
}

static void put_dht(bw_t *w, int tc, int th, const u8 *bits, const u8 *vals, int n)
{
    int i;
    bw_byte(w, 0xFF); bw_byte(w, 0xC4);
    bw_put16(w, (u32)(2 + 1 + 16 + n));
    bw_byte(w, (u32)((tc << 4) | th));
    for (i = 0; i < 16; i++) bw_byte(w, bits[i]);
    for (i = 0; i < n; i++) bw_byte(w, vals[i]);
}

/* Encoder state. Used by the whole-frame jpeg_encode() and (kept alive between bands)
 * by the streaming jpeg_senc_* API. */
struct esctx {
    struct ectx e;
    bw_t w;
    i32 pred[JPEG_MAX_COMP];         /* DC predictors */
    u16 qt[4][64];                   /* copy of the quant tables (zigzag) */
    u32 mcus_x, mcus_y, my;
    int nc, hs[JPEG_MAX_COMP], vs[JPEG_MAX_COMP], tq[JPEG_MAX_COMP];
    int ri, cnt, rst;
    int done;
    u8 fast, wide, tbl_ready;        /* fast transform mode / any q > 255 / tables built for the mode */
};

/* Validate, build tables and write SOI..SOS. whole != 0: also require plane pointers. */
static int enc_begin(struct esctx *s, const jpeg_image *img, u8 *out, unsigned long cap, int whole,
                     jpeg_write_fn wr, void *wctx)
{
    struct ectx *e = &s->e;
    bw_t *w = &s->w;
    u32 W, H;
    int nc, i, k, t, hmax = 1, vmax = 1, used = 0;

    nc = img->ncomp;
    if ((nc != 1 && nc != 3) || img->width <= 0 || img->height <= 0) return JPEG_ERR_ARG;
    if (img->width > 65535 || img->height > 65535) return JPEG_ERR_ARG;
    s->ri = img->restart_interval;
    if (s->ri < 0 || s->ri > 65535) return JPEG_ERR_ARG;

    W = (u32)img->width; H = (u32)img->height;
    s->nc = nc;
    for (i = 0; i < nc; i++) {
        s->hs[i] = (nc == 1) ? 1 : img->comp[i].h;
        s->vs[i] = (nc == 1) ? 1 : img->comp[i].v;
        s->tq[i] = img->comp[i].tq;
        if (s->hs[i] < 1 || s->hs[i] > 4 || s->vs[i] < 1 || s->vs[i] > 4) return JPEG_ERR_ARG;
        if (s->tq[i] < 0 || s->tq[i] > 3) return JPEG_ERR_ARG;
        if (whole && !img->comp[i].data) return JPEG_ERR_ARG;
        if (s->hs[i] > hmax) hmax = s->hs[i];
        if (s->vs[i] > vmax) vmax = s->vs[i];
        used |= 1 << s->tq[i];
    }
    s->mcus_x = cdiv(W, 8u * (u32)hmax);
    s->mcus_y = cdiv(H, 8u * (u32)vmax);
    if (whole) {
        for (i = 0; i < nc; i++) {
            if ((u32)img->comp[i].stride < s->mcus_x * (u32)s->hs[i] * 8u) return JPEG_ERR_ARG;
            if ((u32)img->comp[i].ph < s->mcus_y * (u32)s->vs[i] * 8u) return JPEG_ERR_ARG;
        }
    }

    memcpy(s->qt, img->qt, sizeof s->qt);
    s->wide = 0;
    for (t = 0; t < 4; t++) {
        if (!((used >> t) & 1)) continue;
        for (k = 0; k < 64; k++) {
            if (s->qt[t][k] == 0) return JPEG_ERR_ARG;
            if (s->qt[t][k] > 255) s->wide = 1;
        }
    }
    s->fast = SWJPEG_DEFAULT_XFORM;
    s->tbl_ready = 0;
    memset(e->dc_ent, 0, sizeof e->dc_ent);
    memset(e->ac_ent, 0, sizeof e->ac_ent);
    build_enc(e->dc_ent[0], std_dc_lum_bits, std_dc_vals);
    build_enc(e->dc_ent[1], std_dc_chr_bits, std_dc_vals);
    build_enc(e->ac_ent[0], std_ac_lum_bits, std_ac_lum_vals);
    build_enc(e->ac_ent[1], std_ac_chr_bits, std_ac_chr_vals);

    w->o = out; w->buf = out; w->end = out + cap; w->acc = 0; w->nb = 0; w->ovf = 0;
    w->ioerr = 0; w->wr = wr; w->wctx = wctx; w->flushed = 0;
    w->lim = (cap >= 8) ? (sw_size)(w->end - 8) : 0;
    s->pred[0] = s->pred[1] = s->pred[2] = 0;
    s->my = 0; s->cnt = 0; s->rst = 0; s->done = 0;

    /* SOI + JFIF APP0 */
    bw_byte(w, 0xFF); bw_byte(w, 0xD8);
    bw_byte(w, 0xFF); bw_byte(w, 0xE0); bw_put16(w, 16);
    bw_byte(w, 'J'); bw_byte(w, 'F'); bw_byte(w, 'I'); bw_byte(w, 'F'); bw_byte(w, 0);
    bw_byte(w, 1); bw_byte(w, 1); bw_byte(w, 0);
    bw_put16(w, 1); bw_put16(w, 1); bw_byte(w, 0); bw_byte(w, 0);

    /* DQT: one segment per used table */
    for (t = 0; t < 4; t++) {
        int p16 = 0;
        if (!((used >> t) & 1)) continue;
        for (k = 0; k < 64; k++) if (s->qt[t][k] > 255) p16 = 1;
        bw_byte(w, 0xFF); bw_byte(w, 0xDB);
        bw_put16(w, (u32)(2 + 1 + 64 * (p16 + 1)));
        bw_byte(w, (u32)((p16 << 4) | t));
        for (k = 0; k < 64; k++) {
            if (p16) bw_put16(w, s->qt[t][k]); else bw_byte(w, s->qt[t][k]);
        }
    }

    /* SOF0 */
    bw_byte(w, 0xFF); bw_byte(w, 0xC0);
    bw_put16(w, (u32)(8 + 3 * nc));
    bw_byte(w, 8); bw_put16(w, H); bw_put16(w, W); bw_byte(w, (u32)nc);
    for (i = 0; i < nc; i++) {
        bw_byte(w, (u32)(i + 1));
        bw_byte(w, (u32)((s->hs[i] << 4) | s->vs[i]));
        bw_byte(w, (u32)s->tq[i]);
    }

    /* DHT */
    put_dht(w, 0, 0, std_dc_lum_bits, std_dc_vals, 12);
    put_dht(w, 1, 0, std_ac_lum_bits, std_ac_lum_vals, 162);
    if (nc == 3) {
        put_dht(w, 0, 1, std_dc_chr_bits, std_dc_vals, 12);
        put_dht(w, 1, 1, std_ac_chr_bits, std_ac_chr_vals, 162);
    }

    if (s->ri) { bw_byte(w, 0xFF); bw_byte(w, 0xDD); bw_put16(w, 4); bw_put16(w, (u32)s->ri); }

    /* SOS */
    bw_byte(w, 0xFF); bw_byte(w, 0xDA);
    bw_put16(w, (u32)(6 + 2 * nc));
    bw_byte(w, (u32)nc);
    for (i = 0; i < nc; i++) {
        bw_byte(w, (u32)(i + 1));
        bw_byte(w, i == 0 ? 0x00u : 0x11u);
    }
    bw_byte(w, 0); bw_byte(w, 63); bw_byte(w, 0);
    return bw_status(w);
}

/* quotient n/d, must fit 32 bits (setup code only: no libgcc 64-bit divide) */
static u32 udiv64by32(u64 n, u32 d)
{
    u64 r = 0;
    u32 q = 0;
    int i;
    for (i = 0; i < 64; i++) {
        r = (r << 1) | (n >> 63);
        n <<= 1;
        q <<= 1;
        if (r >= d) { r -= d; q |= 1u; }
    }
    return q;
}

/* quantiser tables for the selected mode, built lazily at the first band */
static void enc_tables(struct esctx *s)
{
    struct ectx *e = &s->e;
    int t, k, i, used = 0;

    for (i = 0; i < s->nc; i++) used |= 1 << s->tq[i];
    for (t = 0; t < 4; t++) {
        if (!((used >> t) & 1)) continue;
        for (k = 0; k < 64; k++) {
            u32 q = s->qt[t][k];
            int nat = zz[k];
            if (s->wide) { e->rec[t][k] = udiv32(0xFFFFFFFFu, q); continue; }
            e->qr[t][nat] = udiv32(1u << 20, q) + 1u;
            e->qb[t][nat] = (u16)(4u * q);
            if (s->fast) {
                u32 aa = (u32)aan14[nat >> 3] * aan14[nat & 7];            /* a_i*a_j in Q28 */
                e->qaan[t][nat] = (i32)udiv32(udiv64by32(1ull << 52, aa), q);
            }
        }
    }
    s->tbl_ready = 1;
}

/* Encode ONE MCU row. base[i]/stride[i]: top-left sample / pitch of the 8*v-row band of
 * component i. */
static int enc_row(struct esctx *s, const u8 *const base[JPEG_MAX_COMP], const int stride[JPEG_MAX_COMP],
                   u32 coef_mask)
{
    bw_t *w = &s->w;
    u32 mx;
    int i, bx, by;

    i16 qz[64] __attribute__((aligned(8)));
    i32 ws[64];

    if (s->my >= s->mcus_y || s->done) return JPEG_ERR_ARG;
    if (!s->tbl_ready) enc_tables(s);
    for (mx = 0; mx < s->mcus_x; mx++) {
        if (s->ri) {
            if (s->cnt == s->ri) {
                bw_flush(w);
                bw_byte(w, 0xFF); bw_byte(w, 0xD0u + (u32)(s->rst & 7));
                s->rst++; s->cnt = 0;
                s->pred[0] = s->pred[1] = s->pred[2] = 0;
            }
            s->cnt++;
        }
        for (i = 0; i < s->nc; i++) {
            const u16 *qt = s->qt[s->tq[i]];
            const u32 *rec = s->e.rec[s->tq[i]];
            int ts = (i == 0) ? 0 : 1;
            for (by = 0; by < s->vs[i]; by++) {
                for (bx = 0; bx < s->hs[i]; bx++) {
                    const u8 *src = base[i] + (sw_size)((u32)by * 8u) * (u32)stride[i]
                                            + (mx * (u32)s->hs[i] + (u32)bx) * 8u;
                    if ((coef_mask >> i) & 1) {            /* quantised coefficients: entropy-code as they are */
                        const i16 *cs = (const i16 *)(const void *)(base[i] + (sw_size)((u32)by * (u32)stride[i])
                                                                    + (sw_size)((mx * (u32)s->hs[i] + (u32)bx) * 128u));
                        huff_block(w, &s->e, ts, cs, &s->pred[i]);
                    } else if (s->wide) {
                        encode_block_wide(w, &s->e, ts, qt, rec, src, stride[i], &s->pred[i]);
                    } else {
                        if (s->fast) {
                            fdct_aan_quant(src, stride[i], s->e.qaan[s->tq[i]], qz);
                        } else {
                            fdct_block(src, stride[i], ws);
                            quant_zz_exact(ws, s->e.qb[s->tq[i]], s->e.qr[s->tq[i]], qz);
                        }
                        huff_block(w, &s->e, ts, qz, &s->pred[i]);
                    }
                }
            }
        }
    }
    s->my++;
    return bw_status(w);
}

static int enc_finish(struct esctx *s, unsigned long *outlen)
{
    bw_t *w = &s->w;
    if (s->my != s->mcus_y || s->done) return JPEG_ERR_STATE;      /* not all MCU rows were encoded */
    bw_flush(w);
    bw_byte(w, 0xFF); bw_byte(w, 0xD9);
    s->done = 1;
    if (w->wr && !w->ovf) bw_full(w);                      /* push the tail through the callback */
    if (w->ovf) return bw_status(w);
    *outlen = (unsigned long)(w->flushed + (u32)(w->o - w->buf));
    return JPEG_OK;
}

unsigned long jpeg_encode_arena_size(void)
{
    return (unsigned long)sizeof(struct esctx) + 32u;
}

/* extra != 0: callback mode, `extra` bytes of write buffer follow the (32-aligned) state */
static struct esctx *esctx_at(void *mem, unsigned long len, u32 extra)
{
    u8 *base = (u8 *)(((unsigned long)mem + 31u) & ~31ul);
    unsigned long need = extra ? (unsigned long)align32((u32)sizeof(struct esctx)) + extra
                               : (unsigned long)sizeof(struct esctx);
    if ((unsigned long)(base - (u8 *)mem) + need > len) return 0;
    return (struct esctx *)(void *)base;
}

int jpeg_encode(const jpeg_image *img, void *arena, unsigned long arenalen,
                unsigned char *out, unsigned long *outlen)
{
    struct esctx *s;
    u32 my;
    int rc, i;

    if (!img || !arena || !out || !outlen) return JPEG_ERR_ARG;
    s = esctx_at(arena, arenalen, 0);
    if (!s) return JPEG_ERR_ARENA;
    rc = enc_begin(s, img, out, *outlen, 1, 0, 0);
    if (rc) return rc;
    for (my = 0; my < s->mcus_y; my++) {
        const u8 *bp[JPEG_MAX_COMP];
        int st[JPEG_MAX_COMP];
        for (i = 0; i < s->nc; i++) {
            bp[i] = img->comp[i].data + (sw_size)(my * (u32)s->vs[i] * 8u) * (u32)img->comp[i].stride;
            st[i] = img->comp[i].stride;
        }
        rc = enc_row(s, bp, st, 0);
        if (rc) return rc;
    }
    return enc_finish(s, outlen);
}

/* ========================================================================= */
/* STREAMING ENCODER                                                         */
/* ========================================================================= */

int jpeg_senc_init(unsigned char *out, unsigned long *outlen, const jpeg_image *meta,
                   void *scratch, unsigned long slen, jpeg_senc *e)
{
    struct esctx *s;
    int rc;

    if (!e) return JPEG_ERR_ARG;
    e->ctx = 0;
    if (!out || !outlen || !meta || !scratch) return JPEG_ERR_ARG;
    s = esctx_at(scratch, slen, 0);
    if (!s) return JPEG_ERR_ARENA;
    rc = enc_begin(s, meta, out, *outlen, 0, 0, 0);
    if (rc) return rc;
    e->ctx = s;
    return JPEG_OK;
}

unsigned long jpeg_senc_cb_scratch_size(void)
{
    return (unsigned long)align32((u32)sizeof(struct esctx)) + (unsigned long)JPEG_WR_BUF + 32u;
}

int jpeg_senc_init_cb(jpeg_write_fn wr, void *wr_ctx, const jpeg_image *meta,
                      void *scratch, unsigned long slen, jpeg_senc *e)
{
    struct esctx *s;
    int rc;

    if (!e) return JPEG_ERR_ARG;
    e->ctx = 0;
    if (!wr || !meta || !scratch) return JPEG_ERR_ARG;
    s = esctx_at(scratch, slen, (u32)JPEG_WR_BUF);
    if (!s) return JPEG_ERR_ARENA;
    rc = enc_begin(s, meta, (u8 *)s + align32((u32)sizeof(struct esctx)), (unsigned long)JPEG_WR_BUF, 0, wr, wr_ctx);
    if (rc) return rc;
    e->ctx = s;
    return JPEG_OK;
}

int jpeg_senc_set_xform(jpeg_senc *e, int mode)
{
    struct esctx *s;
    if (!e || !e->ctx || (mode != JPEG_XFORM_ACCURATE && mode != JPEG_XFORM_FAST)) return JPEG_ERR_ARG;
    s = (struct esctx *)e->ctx;
    if (s->my != 0) return JPEG_ERR_STATE;                 /* only before the first band */
    s->fast = (u8)(mode == JPEG_XFORM_FAST);
    s->tbl_ready = 0;
    return JPEG_OK;
}

int jpeg_senc_band(jpeg_senc *e, const jpeg_comp bands[JPEG_MAX_COMP])
{
    struct esctx *s;
    const u8 *bp[JPEG_MAX_COMP];
    int st[JPEG_MAX_COMP], i;
    u32 cm = 0;

    if (!e || !e->ctx || !bands) return JPEG_ERR_ARG;
    s = (struct esctx *)e->ctx;
    for (i = 0; i < s->nc; i++) {
        u32 unit = bands[i].coef ? 128u : 8u;              /* bytes per block column: int16 x64 or 8 pixels */
        if (!bands[i].data) return JPEG_ERR_ARG;
        if ((u32)bands[i].stride < s->mcus_x * (u32)s->hs[i] * unit) return JPEG_ERR_ARG;
        if ((u32)bands[i].ph < 8u * (u32)s->vs[i]) return JPEG_ERR_ARG;    /* band must hold 8*v rows */
        if (bands[i].coef) cm |= 1u << i;
        bp[i] = bands[i].data;
        st[i] = bands[i].stride;
    }
    return enc_row(s, bp, st, cm);
}

int jpeg_senc_fini(jpeg_senc *e, unsigned long *outlen)
{
    if (!e || !e->ctx || !outlen) return JPEG_ERR_ARG;
    return enc_finish((struct esctx *)e->ctx, outlen);
}

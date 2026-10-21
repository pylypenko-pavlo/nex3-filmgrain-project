# LZPT ('TPZL') tools

Sony CXD4132-era partitions p3/p8 are LZPT-compressed raw images. ma1co's fwtool reads
LZPT; this directory adds a **byte-exact writer** reverse-engineered from the NEX-3N
images (reproduces the stock p3/p8 bit-for-bit, verified by round-trip).

- `lzpt_write.py <inner_image> <out.bin> [--pad <partition_size>]` — pack a decompressed
  inner filesystem image back into a raw LZPT partition image. Format is documented in the
  file header. NB: calls a multiprocessing Pool — import-guard any caller
  (`if __name__=="__main__"`) or it fork-bombs on spawn platforms.
- `lzpt_tok.py` — header/TOC/sub-stream parser used while reversing the format.

Credit: ma1co `fwtool.py` (`fwtool/archive/lzpt.py`, `fwtool/lz77`) — the reader and
starting point. See `notes/firmware-architecture.md` and `notes/live-memory-and-delivery.md`.

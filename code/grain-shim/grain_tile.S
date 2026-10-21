/* Embed the pre-baked grain tile (512x512 int8) as rodata. grain_tile.bin must be in the assembler cwd. */
    .section .rodata
    .align 5
    .global grain_tile
    .type grain_tile, %object
grain_tile:
    .incbin "grain_tile.bin"
    .size grain_tile, 262144
    .section .note.GNU-stack,"",%progbits

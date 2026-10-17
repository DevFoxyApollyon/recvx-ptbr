#ifndef RECVX_TEXREP_H
#define RECVX_TEXREP_H
/* Texture replacements (texrep.c, docs/TEXTURES.md): uploads px (w x h RGBA) to the bound
   GL_TEXTURE_2D, or <mods>/textures/<hash>.png in its place when that file exists. */
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void texrep_teximage(const uint32_t* px, int w, int h);
/* 1 when the texture of that hash was last uploaded from a replacement file */
int texrep_in_use(uint64_t hash);
#ifdef __cplusplus
}
#endif
#endif

/*
 * Texture replacements (PT-BR fork, docs/TEXTURES.md).
 *
 * Every texture the renderer decodes (native or emulated path) is identified by a 64-bit hash of
 * its decoded pixels and size. When <mods>/textures/<hash>.png exists, that image is uploaded
 * instead: it may be larger than the original (an upscale) - the shaders sample in normalized
 * coordinates, so only the detail changes - or edited (a translated menu plate).
 * With the menus in Portuguese, <mods>/textures/pt/<hash>.png comes first (translated pictures).
 * RECVX_TEX_DUMP=dir saves each decoded texture once as <hash>.png, to edit or upscale.
 *
 * Render thread only.
 */
#include "texrep.h"
#include "../render/gl_loader.h"
#include "../host/lang.h"
#include <SDL3/SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_NO_STDIO
#include "stb_image.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#define STBI_WRITE_NO_STDIO
#include "stb_image_write.h"

void host_log(const char* fmt, ...);
FILE* pc_fopen(const char* path, const char* mode);

/* hashes already looked up: replaced or not (a decode miss is rare, but a missing file should
   not cost a file system lookup every time) */
#define SEEN_N 8192
static uint64_t seen[SEEN_N];
static unsigned char seen_has[SEEN_N];
static int seen_used[SEEN_N];
static int seen_lang = -1;          /* language the lookups were made for */
static uint64_t last_replaced[16];  /* recent replacements, for texrep_in_use */
static int last_n;

static uint64_t hash_pixels(const uint32_t* px, int w, int h)
{
    uint64_t x = 1469598103934665603ull ^ ((uint64_t)w << 32 | (uint32_t)h);
    const uint32_t* end = px + (size_t)w * h;
    for (; px < end; px++) { x ^= *px; x *= 1099511628211ull; }
    return x;
}

static const char* mods_dir(void)
{
    const char* d = SDL_getenv("RECVX_MODS");
    return d && *d ? d : "mods";
}

static unsigned char* read_file(const char* path, size_t* n)
{
    FILE* f = pc_fopen(path, "rb");
    unsigned char* buf;
    long len;
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    len = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (len <= 0 || !(buf = malloc((size_t)len))) { fclose(f); return NULL; }
    *n = fread(buf, 1, (size_t)len, f);
    fclose(f);
    return buf;
}

static void write_cb(void* ctx, void* data, int size) { fwrite(data, 1, (size_t)size, (FILE*)ctx); }

static void dump(uint64_t h, const uint32_t* px, int w, int hgt)
{
    static const char* dir;
    static int checked;
    char path[1024];
    FILE* f;
    if (!checked++) dir = SDL_getenv("RECVX_TEX_DUMP");
    if (!dir || !*dir) return;
    snprintf(path, sizeof path, "%s/%016llx.png", dir, (unsigned long long)h);
    if ((f = pc_fopen(path, "rb"))) { fclose(f); return; }   /* already there */
    if (!(f = pc_fopen(path, "wb"))) return;
    stbi_write_png_to_func(write_cb, f, w, hgt, 4, px, w * 4);
    fclose(f);
}

static int slot_of(uint64_t h)
{
    uint32_t i = (uint32_t)(h ^ (h >> 32)) & (SEEN_N - 1);
    for (int k = 0; k < SEEN_N; k++, i = (i + 1) & (SEEN_N - 1))
        if (!seen_used[i] || seen[i] == h) return (int)i;
    return -1;
}

int texrep_in_use(uint64_t hash)
{
    for (int i = 0; i < 16; i++)
        if (last_replaced[i] == hash) return 1;
    return 0;
}

static void note(uint64_t hs, int replaced)
{
    int i;
    for (i = 0; i < 16 && last_replaced[i] != hs; i++) {}
    if (replaced && i == 16) last_replaced[last_n++ & 15] = hs;
    if (!replaced && i < 16) last_replaced[i] = 0;
}

void texrep_teximage(const uint32_t* px, int w, int h)
{
    uint64_t hs = hash_pixels(px, w, h);
    int s;
    if (seen_lang != g_lang) { memset(seen_used, 0, sizeof seen_used); seen_lang = g_lang; }
    s = slot_of(hs);
    dump(hs, px, w, h);
    if (s >= 0 && seen_used[s] && !seen_has[s]) goto original;
    {
        char path[1024];
        size_t n = 0;
        unsigned char* file;
        file = NULL;
        if (g_lang == LANG_PT) {
            snprintf(path, sizeof path, "%s/textures/pt/%016llx.png", mods_dir(), (unsigned long long)hs);
            file = read_file(path, &n);
        }
        if (!file) {
            snprintf(path, sizeof path, "%s/textures/%016llx.png", mods_dir(), (unsigned long long)hs);
            file = read_file(path, &n);
        }
        if (s >= 0) { seen_used[s] = 1; seen[s] = hs; seen_has[s] = file != NULL; }
        if (file) {
            int rw, rh, comp;
            unsigned char* img = stbi_load_from_memory(file, (int)n, &rw, &rh, &comp, 4);
            free(file);
            if (img) {
                glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, rw, rh, 0, GL_RGBA, GL_UNSIGNED_BYTE, img);
                stbi_image_free(img);
                note(hs, 1);
                host_log("textures: %016llx replaced (%dx%d -> %dx%d)\n", (unsigned long long)hs, w, h, rw, rh);
                return;
            }
            host_log("textures: %s is not a readable PNG\n", path);
            if (s >= 0) seen_has[s] = 0;
        }
    }
original:
    note(hs, 0);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, px);
}

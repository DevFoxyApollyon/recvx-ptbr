/* Menu language and the accented letters of the game's font (lang.h). */
#include "lang.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <SDL3/SDL.h>
void host_log(const char* fmt, ...);
FILE* pc_fopen(const char* path, const char* mode);

int g_lang = LANG_PT;

/* ---------------------------------------------------------------- translations */
typedef struct { const char* en; const char* pt; } LangEntry;

static const LangEntry table_pt[] = {
#include "lang_ptbr.inc"
};
enum { TABLE_N = sizeof table_pt / sizeof table_pt[0] };

/* Open-addressing hash of the English strings, built on first use. */
enum { HASH_N = 4096 };
static short hash_slot[HASH_N];
static int hash_ready;

static uint32_t hash_str(const char* s)
{
    uint32_t h = 2166136261u;
    while (*s) h = (h ^ (unsigned char)*s++) * 16777619u;
    return h;
}

static void build_hash(void)
{
    for (int i = 0; i < HASH_N; i++) hash_slot[i] = -1;
    for (int i = 0; i < TABLE_N; i++) {
        uint32_t h = hash_str(table_pt[i].en) & (HASH_N - 1);
        while (hash_slot[h] >= 0) h = (h + 1) & (HASH_N - 1);
        hash_slot[h] = (short)i;
    }
    hash_ready = 1;
}

const char* L(const char* en)
{
    if (!en || g_lang != LANG_PT || !*en) return en;
    if (!hash_ready) build_hash();
    for (uint32_t h = hash_str(en) & (HASH_N - 1);; h = (h + 1) & (HASH_N - 1)) {
        int i = hash_slot[h];
        if (i < 0) return en;
        if (strcmp(table_pt[i].en, en) == 0) return table_pt[i].pt;
    }
}

/* ---------------------------------------------------------------- glyphs */
/* Keep in sync with pc/tools/text.py EXTRA_GLYPHS and decomp message.c FontSz. */
typedef struct { unsigned cp; unsigned short code; char base; unsigned char mark; } Extra;
enum { M_ACUTE, M_GRAVE, M_CIRCUMFLEX, M_TILDE, M_DIAERESIS, M_CEDILLA };
static const Extra extras[] = {
    { 0xE1, 108, 'a', M_ACUTE }, { 0xE0, 109, 'a', M_GRAVE }, { 0xE2, 110, 'a', M_CIRCUMFLEX }, { 0xE3, 111, 'a', M_TILDE },
    { 0xE9, 112, 'e', M_ACUTE }, { 0xEA, 113, 'e', M_CIRCUMFLEX }, { 0xED, 114, 'i', M_ACUTE }, { 0xF3, 115, 'o', M_ACUTE },
    { 0xF4, 116, 'o', M_CIRCUMFLEX }, { 0xF5, 117, 'o', M_TILDE }, { 0xFA, 118, 'u', M_ACUTE }, { 0xFC, 119, 'u', M_DIAERESIS },
    { 0xE7, 120, 'c', M_CEDILLA },
    { 0xC1, 121, 'A', M_ACUTE }, { 0xC0, 122, 'A', M_GRAVE }, { 0xC2, 123, 'A', M_CIRCUMFLEX }, { 0xC3, 124, 'A', M_TILDE },
    { 0xC9, 125, 'E', M_ACUTE }, { 0xCA, 126, 'E', M_CIRCUMFLEX }, { 0xCD, 127, 'I', M_ACUTE }, { 0xD3, 128, 'O', M_ACUTE },
    { 0xD4, 129, 'O', M_CIRCUMFLEX }, { 0xD5, 130, 'O', M_TILDE }, { 0xDA, 131, 'U', M_ACUTE }, { 0xC7, 132, 'C', M_CEDILLA },
    { 0xF1, 133, 'n', M_TILDE }, { 0xD1, 134, 'N', M_TILDE },
};
enum { EXTRA_N = sizeof extras / sizeof extras[0] };

unsigned lang_next_cp(const char** sp)
{
    const unsigned char* s = (const unsigned char*)*sp;
    unsigned c = *s;
    if (!c) return 0;
    if (c < 0x80) { *sp += 1; return c; }
    if ((c & 0xE0) == 0xC0 && (s[1] & 0xC0) == 0x80) { *sp += 2; return ((c & 0x1F) << 6) | (s[1] & 0x3F); }
    if ((c & 0xF0) == 0xE0 && (s[1] & 0xC0) == 0x80 && (s[2] & 0xC0) == 0x80) {
        *sp += 3;
        return ((c & 0x0F) << 12) | ((s[1] & 0x3F) << 6) | (s[2] & 0x3F);
    }
    *sp += 1;
    return '?';
}

/* The game-font menus show accented letters as their base letter (OPÇÕES -> OPCOES): the font's
   accented glyphs are only drawn on some load paths, a plain letter always works. */
unsigned short lang_glyph(unsigned cp)
{
    if (cp >= 33 && cp < 127) return (unsigned short)(cp - 32);
    for (int i = 0; i < EXTRA_N; i++)
        if (extras[i].cp == cp) return (unsigned short)(extras[i].base - 32);
    return 0xFFFF;
}

/* "ação" -> "acao": accented letters to their base letter, other non-ASCII to '?' */
void lang_strip_accents(char* s)
{
    const char* r = s;
    char* w = s;
    unsigned cp;
    while ((cp = lang_next_cp(&r)) != 0) {
        if (cp < 128) { *w++ = (char)cp; continue; }
        unsigned short g = lang_glyph(cp);
        *w++ = g != 0xFFFF ? (char)(g + 32) : '?';
    }
    *w = 0;
}

int lang_to_glyphs(const char* s, unsigned short* out, int max)
{
    int n = 0;
    unsigned cp;
    while ((cp = lang_next_cp(&s)) != 0) {
        unsigned short g = cp == ' ' ? 0xFF01 : lang_glyph(cp);
        if (g == 0xFFFF) g = (unsigned short)('?' - 32);
        if (out && n < max) out[n] = g;
        n++;
    }
    return n;
}

/* ---------------------------------------------------------------- font patch */
/* Same drawing as pc/tools/font.py: copy the base letter, add the mark in the font's style
   (palette 7 outline, 2 fill); capitals are squashed to make room above. */
enum { CELL = 28, PER_ROW = 18, OUTLINE = 7, FILL = 2 };
static const signed char mark_px[6][14][2] = {
    [M_ACUTE] = { {0,4},{1,4},{1,3},{2,3},{2,2},{3,2},{3,1},{4,1},{4,0},{5,0},{-1,-1} },
    [M_GRAVE] = { {5,4},{4,4},{4,3},{3,3},{3,2},{2,2},{2,1},{1,1},{1,0},{0,0},{-1,-1} },
    [M_CIRCUMFLEX] = { {0,4},{1,3},{1,4},{2,2},{2,3},{3,1},{3,2},{4,2},{4,3},{5,3},{5,4},{6,4},{3,0},{-1,-1} },
    [M_TILDE] = { {0,3},{0,2},{1,1},{2,1},{2,0},{3,1},{4,2},{5,2},{5,3},{6,2},{7,1},{7,0},{-1,-1} },
    [M_DIAERESIS] = { {0,1},{1,1},{0,2},{1,2},{5,1},{6,1},{5,2},{6,2},{-1,-1} },
    [M_CEDILLA] = { {2,0},{2,1},{3,2},{4,3},{3,4},{2,4},{1,4},{-1,-1} },
};

typedef struct { unsigned char* img; int w; } FontPage;

static int px_get(const FontPage* p, int x, int y)
{
    unsigned char b = p->img[(y * p->w + x) / 2];
    return (x & 1) ? b >> 4 : b & 15;
}
static void px_put(FontPage* p, int x, int y, int v)
{
    unsigned char* b = &p->img[(y * p->w + x) / 2];
    *b = (x & 1) ? (unsigned char)((*b & 0x0F) | (v << 4)) : (unsigned char)((*b & 0xF0) | v);
}

static void draw_extra(FontPage* p, const Extra* e)
{
    unsigned char c[CELL][CELL], o[CELL][CELL];
    int bx = ((e->base - 32) % PER_ROW) * CELL, by = ((e->base - 32) / PER_ROW) * CELL;
    int x0 = CELL, x1 = -1, y0 = CELL, y1 = -1, mw = 0, mh = 0;
    for (int y = 0; y < CELL; y++)
        for (int x = 0; x < CELL; x++) {
            c[y][x] = (unsigned char)px_get(p, bx + x, by + y);
            if (c[y][x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
        }
    if (x1 < 0) return;
    for (int i = 0; mark_px[e->mark][i][0] >= 0; i++) {
        if (mark_px[e->mark][i][0] + 1 > mw) mw = mark_px[e->mark][i][0] + 1;
        if (mark_px[e->mark][i][1] + 1 > mh) mh = mark_px[e->mark][i][1] + 1;
    }
    int cx = (x0 + x1 + 1) / 2 - mw / 2, oy;
    if (e->mark == M_CEDILLA) oy = y1 + 1;
    else {
        if (e->base >= 'A' && e->base <= 'Z') {   /* squash rows y0..y1 into y0+mh+2..y1 */
            int top = y0 + mh + 2;
            memcpy(o, c, sizeof c);
            for (int y = 0; y < CELL; y++)
                if (y <= y1) memset(c[y], 0, CELL);
            for (int y = top; y <= y1; y++) {
                int src = y0 + ((y - top) * (y1 - y0) + (y1 - top) / 2) / (y1 - top ? y1 - top : 1);
                memcpy(c[y], o[src], CELL);
            }
            y0 = top;
        }
        if (e->base == 'i') {                     /* the dot makes way for the mark */
            for (int y = y0; y < y0 + 6 && y < CELL; y++) memset(c[y], 0, CELL);
            while (y0 < CELL && !memchr(c[y0], 0, CELL) && 0) y0++;
            for (y0 = 0; y0 < CELL; y0++) { int any = 0; for (int x = 0; x < CELL; x++) any |= c[y0][x]; if (any) break; }
        }
        oy = y0 - mh - 1;
        if (oy < 0) oy = 0;
    }
    unsigned char m[CELL][CELL] = {{0}};
    for (int i = 0; mark_px[e->mark][i][0] >= 0; i++) {
        int x = cx + mark_px[e->mark][i][0], y = oy + mark_px[e->mark][i][1];
        if (x >= 0 && x < CELL && y >= 0 && y < CELL) m[y][x] = 1;
    }
    for (int y = 0; y < CELL; y++)
        for (int x = 0; x < CELL; x++) {
            if (!m[y][x]) continue;
            for (int dy = -1; dy <= 1; dy++)
                for (int dx = -1; dx <= 1; dx++) {
                    int nx = x + dx, ny = y + dy;
                    if (nx >= 0 && nx < CELL && ny >= 0 && ny < CELL && !m[ny][nx] && !c[ny][nx]) c[ny][nx] = OUTLINE;
                }
        }
    for (int y = 0; y < CELL; y++)
        for (int x = 0; x < CELL; x++)
            if (m[y][x]) c[y][x] = FILL;
    int tx = (e->code % PER_ROW) * CELL, ty = (e->code / PER_ROW) * CELL;
    for (int y = 0; y < CELL; y++)
        for (int x = 0; x < CELL; x++) px_put(p, tx + x, ty + y, c[y][x]);
}

void lang_patch_font(unsigned char* d, unsigned size)
{
    /* first texture: "TIM2" with a second "TIM2" 32 bytes in, picture header at +0xA0 */
    for (unsigned o = 0; o + 0xC0 < size; o += 4) {
        if (memcmp(d + o, "TIM2", 4) || memcmp(d + o + 32, "TIM2", 4)) continue;
        const unsigned char* h = d + o + 0xA0;
        unsigned img_size = h[8] | h[9] << 8 | h[10] << 16 | (unsigned)h[11] << 24;
        unsigned hdr = h[12] | h[13] << 8;
        int type = h[19], w = h[20] | h[21] << 8, hgt = h[22] | h[23] << 8;
        if (type != 4 || w != 512 || hgt != 512 || o + 0xA0 + hdr + img_size > size) return;
        FontPage p = { d + o + 0xA0 + hdr, w };
        /* already patched (a font mod from pc/tools/font.py): leave it */
        for (int y = 0; y < CELL; y++)
            for (int x = 0; x < CELL; x++)
                if (px_get(&p, (108 % PER_ROW) * CELL + x, (108 / PER_ROW) * CELL + y)) return;
        for (int i = 0; i < EXTRA_N; i++) draw_extra(&p, &extras[i]);
        return;
    }
}

/* The game over screen's "Retry? Yes No" (gameover.c cnt_mes, glyph codes in the code, not on
   the disc): the same layout in Portuguese. Yes and No keep their places (the cursor is drawn at
   fixed x), so Sim and Nao start where Yes and No did. */
const unsigned short* pc_continue_mes(const unsigned short* en)
{
    static unsigned short pt[32];
    if (g_lang != LANG_PT) return en;
    if (!pt[0]) {
        static const char* parts[] = { "\x01" "Continuar?", "\x00", "\x01" "Sim", "\x01\x01" "Nao", NULL };
        int n = 0;
        for (int i = 0; parts[i]; i++) {
            const char* c = parts[i];
            if (*c == 1) { pt[n++] = 0xFF01; c++; if (*c == 1) { pt[n++] = 0xFF01; c++; } }
            else if (*c == 0 && !c[1]) { pt[n++] = 0xFF00; continue; }
            for (; *c; c++) pt[n++] = (unsigned short)(*c - 32);
        }
        pt[n] = 0xFFFF;
    }
    return pt;
}

/* Room messages in Portuguese (pc/tools/text.py import --tables): <mods>/textos/RM_xxxx.mes is
   the room's message table (u32 entry 0, u32 offsets, u16 strings) built from pc/ptbr/salas, used
   in place of the one inside the room file. Rooms without one keep the disc text. */
unsigned int* pc_room_mes(unsigned int* mesp, int stg, int rno, int rcase)
{
    static unsigned int* buf;
    char path[512];
    const char* mods = SDL_getenv("RECVX_MODS");
    FILE* f;
    long n;
    if (buf) { SDL_free(buf); buf = NULL; }
    if (g_lang != LANG_PT || !mesp) return mesp;
    SDL_snprintf(path, sizeof path, "%s/textos/RM_%d%02d%d.mes", mods && *mods ? mods : "mods", stg, rno, rcase);
    if (!(f = pc_fopen(path, "rb"))) return mesp;
    fseek(f, 0, SEEK_END);
    n = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (n >= 8 && (buf = SDL_malloc((size_t)n)) && fread(buf, 1, (size_t)n, f) == (size_t)n) {
        fclose(f);
        host_log("lang: %s\n", path);
        return buf;
    }
    fclose(f);
    if (buf) { SDL_free(buf); buf = NULL; }
    return mesp;
}

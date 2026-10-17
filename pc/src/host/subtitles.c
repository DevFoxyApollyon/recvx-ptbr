/* Subtitles for voiced lines (subtitles.h).

   <mods>/legendas.txt:

       # comments
       [VOICE1.AFS/12]
       0.0  Primeira frase da fala.
       2.4  Segunda frase|em duas linhas.
       [VOICE1.AFS/13]
       Uma frase sem tempo: fica na tela durante a fala inteira.

   A line may start with a time (seconds, or m:ss.s) from the start of the voiced line; each cue
   stays until the next one or the end of the line. '|' breaks the line on screen. The file is
   read again when it changes, so it can be edited while the game runs. */
#include "subtitles.h"
#include "lang.h"

#include <SDL3/SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

int g_sub_on = 1;
int g_sub_size = 100;
int g_sub_ids = 0;

void host_log(const char* fmt, ...);
FILE* pc_fopen(const char* path, const char* mode);

/* ---------------------------------------------------------------- the file */
typedef struct { float t; char* text; } Cue;
typedef struct { char key[48]; int first, n; } Entry;

static Cue* cues;
static int cue_n, cue_cap;
static Entry* entries;
static int entry_n, entry_cap;
static char* text_pool;               /* all cue texts, freed on reload */
static size_t pool_len, pool_cap;
static time_t file_mtime;
static Uint64 next_check;

static const char* file_path(char* buf, size_t n)
{
    const char* dir = SDL_getenv("RECVX_MODS") ? SDL_getenv("RECVX_MODS") : "mods";
    snprintf(buf, n, "%s/legendas.txt", dir);
    return buf;
}

static void clear_all(void)
{
    free(cues); free(entries); free(text_pool);
    cues = NULL; entries = NULL; text_pool = NULL;
    cue_n = cue_cap = entry_n = entry_cap = 0;
    pool_len = pool_cap = 0;
}

static size_t pool_add(const char* s, size_t len)
{
    if (pool_len + len + 1 > pool_cap) {
        pool_cap = (pool_len + len + 1) * 2 + 4096;
        text_pool = realloc(text_pool, pool_cap);
    }
    memcpy(text_pool + pool_len, s, len);
    text_pool[pool_len + len] = 0;
    pool_len += len + 1;
    return pool_len - len - 1;
}

/* "12.5", "1:02.3" at the start of s: the time and where the text starts, or -1 */
static float parse_time(const char* s, const char** rest)
{
    char* e;
    double a = strtod(s, &e);
    if (e == s) return -1;
    if (*e == ':') {
        char* e2;
        double b = strtod(e + 1, &e2);
        if (e2 == e + 1) return -1;
        a = a * 60 + b;
        e = e2;
    }
    if (*e != ' ' && *e != '\t') return -1;
    while (*e == ' ' || *e == '\t') e++;
    *rest = e;
    return (float)a;
}

static void load(void)
{
    char path[512], line[1024];
    size_t* offs = NULL;
    int offs_n = 0, offs_cap = 0;
    FILE* f = pc_fopen(file_path(path, sizeof path), "rb");
    clear_all();
    if (!f) return;
    Entry* cur = NULL;
    while (fgets(line, sizeof line, f)) {
        char* s = line;
        size_t len = strlen(s);
        while (len && (s[len - 1] == '\n' || s[len - 1] == '\r' || s[len - 1] == ' ' || s[len - 1] == '\t')) s[--len] = 0;
        if (!strncmp(s, "\xEF\xBB\xBF", 3)) { s += 3; len -= 3; }   /* UTF-8 BOM */
        while (*s == ' ' || *s == '\t') { s++; len--; }
        if (!*s || *s == '#') continue;
        if (*s == '[') {
            char* end = strchr(s, ']');
            if (!end) continue;
            *end = 0;
            if (entry_n == entry_cap) { entry_cap = entry_cap * 2 + 64; entries = realloc(entries, entry_cap * sizeof *entries); }
            cur = &entries[entry_n++];
            snprintf(cur->key, sizeof cur->key, "%s", s + 1);
            for (char* k = cur->key; *k; k++) if (*k >= 'a' && *k <= 'z') *k -= 32;
            cur->first = cue_n;
            cur->n = 0;
            continue;
        }
        if (!cur) continue;
        const char* text = s;
        float t = parse_time(s, &text);
        if (t < 0 && cur->n) {                  /* untimed after the first: one more line of the same cue */
            size_t prev = offs[offs_n - 1], plen = strlen(text_pool + prev), tlen = strlen(text);
            char* joined = malloc(plen + tlen + 2);
            memcpy(joined, text_pool + prev, plen);
            joined[plen] = '|';
            memcpy(joined + plen + 1, text, tlen + 1);
            offs[offs_n - 1] = pool_add(joined, plen + tlen + 1);
            free(joined);
            continue;
        }
        if (t < 0) t = 0;
        if (cue_n == cue_cap) { cue_cap = cue_cap * 2 + 256; cues = realloc(cues, cue_cap * sizeof *cues); }
        if (offs_n == offs_cap) { offs_cap = offs_cap * 2 + 256; offs = realloc(offs, offs_cap * sizeof *offs); }
        offs[offs_n++] = pool_add(text, strlen(text));
        cues[cue_n].t = t;
        cues[cue_n].text = NULL;
        cue_n++;
        cur->n++;
    }
    fclose(f);
    for (int i = 0; i < cue_n; i++) {          /* the pool may have moved while growing */
        cues[i].text = text_pool + offs[i];
        for (char* p = cues[i].text; *p; p++) if (*p == '|') *p = '\n';
    }
    free(offs);
    host_log("subtitles: %s: %d lines, %d cues\n", path, entry_n, cue_n);
}

static void check_file(void)
{
    char path[512];
    struct stat st;
    Uint64 now = SDL_GetTicks();
    if (now < next_check) return;
    next_check = now + 2000;
    time_t m = stat(file_path(path, sizeof path), &st) == 0 ? st.st_mtime : 0;
    if (m != file_mtime) { file_mtime = m; load(); }
}

static const Entry* find(const char* key)
{
    for (int i = 0; i < entry_n; i++)
        if (!strcmp(entries[i].key, key)) return &entries[i];
    return NULL;
}

/* ---------------------------------------------------------------- playing lines */
enum { MAX_ACTIVE = 8 };
typedef struct { const void* talk; char key[48]; uint32_t rate; Uint64 ended_at; } Active;
static Active active[MAX_ACTIVE];
static SDL_Mutex* lock;
static int is_voice_key(const char* key) { return !strncmp(key, "VOICE", 5); }

static void lock_init(void) { if (!lock) lock = SDL_CreateMutex(); }

void subtitles_voice_start(const void* talk, const char* key, uint32_t rate)
{
    int i, slot = -1;
    lock_init();
    SDL_LockMutex(lock);
    for (i = 0; i < MAX_ACTIVE; i++) if (active[i].talk == talk) slot = i;
    for (i = 0; slot < 0 && i < MAX_ACTIVE; i++) if (!active[i].talk) slot = i;
    if (slot < 0) slot = 0;
    active[slot].talk = talk;
    snprintf(active[slot].key, sizeof active[slot].key, "%s", key);
    for (char* k = active[slot].key; *k; k++) if (*k >= 'a' && *k <= 'z') *k -= 32;
    active[slot].rate = rate ? rate : 1;
    active[slot].ended_at = 0;
    SDL_UnlockMutex(lock);
    if (is_voice_key(active[slot].key)) host_log("subtitles: voice %s\n", active[slot].key);
}

void subtitles_voice_stop(const void* talk)
{
    lock_init();
    SDL_LockMutex(lock);
    for (int i = 0; i < MAX_ACTIVE; i++) if (active[i].talk == talk) active[i].talk = NULL;
    SDL_UnlockMutex(lock);
}

/* voice files only: music (BGM*.AFS) and sound banks never get a key on screen */
static int is_voice(const char* key) { return !strncmp(key, "VOICE", 5); }

int subtitles_current(char* buf, int n, int* is_id)
{
    int found = 0;
    static char last[256];
    *is_id = 0;
    if (!g_sub_on) return 0;
    {   /* RECVX_SUB_TEST="text": always show this text (test aid for the drawing) */
        const char* test = SDL_getenv("RECVX_SUB_TEST");
        if (test && *test) { snprintf(buf, n, "%s", test); for (char* c = buf; *c; c++) if (*c == '|') *c = 10; lang_strip_accents(buf); return 1; }
    }
    lock_init();
    check_file();
    SDL_LockMutex(lock);
    for (int i = 0; i < MAX_ACTIVE && !found; i++) {
        Active* a = &active[i];
        int ended = 0;
        if (!a->talk) continue;
        uint64_t pos = adx_talk_position(a->talk, &ended);
        if (ended) {   /* keep the last cue up a moment after the voice ends */
            if (!a->ended_at) a->ended_at = SDL_GetTicks();
            if (SDL_GetTicks() - a->ended_at > 600) { a->talk = NULL; continue; }
        }
        const Entry* e = find(a->key);
        if (!e || !e->n) {
            if (g_sub_ids && is_voice(a->key) && !ended) { snprintf(buf, n, "[%s]", a->key); *is_id = 1; found = 1; }
            continue;
        }
        float t = (float)pos / (float)a->rate;
        int pick = 0;
        for (int k = 1; k < e->n; k++)
            if (cues[e->first + k].t <= t) pick = k;
        snprintf(buf, n, "%s", cues[e->first + pick].text);
        found = 1;
    }
    SDL_UnlockMutex(lock);
    if (found) lang_strip_accents(buf);   /* no accents on screen, as asked: "acao" for "ação" */
    if (strncmp(last, found ? buf : "", sizeof last - 1)) {   /* log what the screen shows, once per change */
        snprintf(last, sizeof last, "%s", found ? buf : "");
        host_log("subtitles: showing \"%.60s\"\n", last);
    }
    return found;
}

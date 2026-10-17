/* Subtitles for the game's voiced lines (PT-BR fork, docs/SUBTITLES.md).

   Every spoken line is an ADX stream the game starts by AFS entry (adx.c ADXT_StartAfs), e.g.
   VOICE1.AFS/12. <mods>/legendas.txt maps those keys to text, optionally timed against the
   line's own playback, and the overlay draws the current text at the bottom of the screen.
   The file is the player's own (it holds a translation of the game's script): it is never part
   of the repository. */
#ifndef RECVX_SUBTITLES_H
#define RECVX_SUBTITLES_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

extern int g_sub_on;      /* recvx.ini subtitles: show subtitles */
extern int g_sub_size;    /* subtitle_size: percent of the default text size */
extern int g_sub_ids;     /* subtitle_ids: show the key of a voiced line that has no subtitle */

/* game thread (adx.c) */
void subtitles_voice_start(const void* talk, const char* key, uint32_t rate);
void subtitles_voice_stop(const void* talk);

/* main thread (overlay): the text to show now (UTF-8, '\n' breaks lines); 0 when none.
   *is_id is set when the text is only the key of a line without a subtitle. */
int subtitles_current(char* buf, int n, int* is_id);

/* adx.c: samples of `talk` played so far, and whether it ended */
uint64_t adx_talk_position(const void* talk, int* ended);

#ifdef __cplusplus
}
#endif
#endif

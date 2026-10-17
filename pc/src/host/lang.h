/* Menu language (PT-BR fork). The port's menus keep their English text in the code and call L()
   when they draw: with the language set to Portuguese, L() returns the text of
   lang_ptbr.inc (UTF-8), otherwise the English text unchanged. Strings without a translation
   stay English. pc/tools/lang_extract.py lists the ones still missing. */
#ifndef RECVX_LANG_H
#define RECVX_LANG_H
#ifdef __cplusplus
extern "C" {
#endif

enum { LANG_EN, LANG_PT, LANG_COUNT };
extern int g_lang;                         /* recvx.ini "language" */

const char* L(const char* en);             /* translated text, or en */

/* UTF-8 text -> the game's u16 glyph codes (message.c bhDispMessage): ASCII c -> c - 32, the
   accented letters -> the extra glyphs lang.c draws into the font (codes 108..), anything else
   -> '?'. Returns the number of codes written (no terminator); out may be NULL to count. */
int lang_to_glyphs(const char* utf8, unsigned short* out, int max);
/* Next code point of a UTF-8 string, advancing *s (0 at the end). */
unsigned lang_next_cp(const char** s);
/* Glyph code of one code point (0xFFFF when the font has none). */
unsigned short lang_glyph(unsigned cp);
/* In place: accented letters to their base letter (subtitles and game-font menus avoid accents). */
void lang_strip_accents(char* s);

/* Draws the accented letters into the game's message font (SYSEFF.ALD's first texture) while
   it is in memory, before the game uploads it: data is the loaded file, size its length. */
void lang_patch_font(unsigned char* data, unsigned size);

#ifdef __cplusplus
}
#endif
#endif

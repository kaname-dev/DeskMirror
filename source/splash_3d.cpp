#include "splash_3d.h"

#include <3ds.h>
#include <cstring>

#define SPLASH_W 400
#define SPLASH_H 240
#define PARALLAX_MAX 10

static inline u32 topOff(u16 x, u16 y) {
    return (SPLASH_H - y + x * SPLASH_H) * 3;
}

static void putPx(u8* fb, s16 x, s16 y, u8 r, u8 g, u8 b) {
    if (!fb || x < 0 || y < 0 || x >= SPLASH_W || y >= SPLASH_H)
        return;
    u32 o = topOff((u16)x, (u16)y);
    fb[o] = r;
    fb[o + 1] = g;
    fb[o + 2] = b;
}

static void fillEye(u8* fb, u8 r, u8 g, u8 b) {
    if (!fb)
        return;
    for (u16 y = 0; y < SPLASH_H; y++) {
        for (u16 x = 0; x < SPLASH_W; x++) {
            u32 o = topOff(x, y);
            fb[o] = r;
            fb[o + 1] = g;
            fb[o + 2] = b;
        }
    }
}

static s16 depthShift(u8 depth) {
    return (s16)((depth * PARALLAX_MAX) / 255);
}

static void rectStereo(s16 x, s16 y, s16 w, s16 h, u8 depth, u8 r, u8 g, u8 b) {
    u8* left = (u8*)gfxGetFramebuffer(GFX_TOP, GFX_LEFT, nullptr, nullptr);
    u8* right = (u8*)gfxGetFramebuffer(GFX_TOP, GFX_RIGHT, nullptr, nullptr);
    s16 sh = depthShift(depth);
    for (s16 py = y; py < y + h; py++) {
        for (s16 px = x; px < x + w; px++) {
            putPx(left, px - sh, py, r, g, b);
            putPx(right, px + sh, py, r, g, b);
        }
    }
}

static char glyphAt(char c, int row, int col) {
    static const char g3[7][6] = {" ### ", "    #", "  ## ", "    #", " ### ", "     ", "     "};
    static const char gD[7][6] = {" ##  ", " # # ", " # # ", " # # ", " ##  ", "     ", "     "};
    static const char gS[7][6] = {"  ## ", " #   ", "  #  ", "   # ", " ##  ", "     ", "     "};
    static const char gM[7][6] = {" # # ", " ### ", " # # ", " # # ", " # # ", "     ", "     "};
    static const char gO[7][6] = {" ### ", " # # ", " # # ", " # # ", " ### ", "     ", "     "};
    static const char gN[7][6] = {" # # ", " ### ", " ### ", " # # ", " # # ", "     ", "     "};
    static const char gI[7][6] = {" ### ", "  #  ", "  #  ", "  #  ", " ### ", "     ", "     "};
    static const char gT[7][6] = {" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "     "};
    static const char gE[7][6] = {" ### ", " #   ", " ##  ", " #   ", " ### ", "     ", "     "};
    static const char gR[7][6] = {" ##  ", " # # ", " ##  ", " # # ", " # # ", "     ", "     "};
    static const char gSp[7][6] = {"     ", "     ", "     ", "     ", "     ", "     ", "     "};
    const char (*g)[6] = gSp;

    switch (c) {
    case '3': g = g3; break;
    case 'D': g = gD; break;
    case 'S': g = gS; break;
    case 'M': g = gM; break;
    case 'O': g = gO; break;
    case 'N': g = gN; break;
    case 'I': g = gI; break;
    case 'T': g = gT; break;
    case 'E': g = gE; break;
    case 'R': g = gR; break;
    default: break;
    }
    if (row < 0 || row >= 7 || col < 0 || col >= 5)
        return ' ';
    return g[row][col];
}

static void textStereo(const char* text, s16 x0, s16 y0, u8 depth, u8 scale, u8 r, u8 g, u8 b) {
    s16 cx = x0;
    for (const char* p = text; *p; p++) {
        for (int row = 0; row < 7; row++) {
            for (int col = 0; col < 5; col++) {
                if (glyphAt(*p, row, col) != '#')
                    continue;
                for (u8 sy = 0; sy < scale; sy++) {
                    for (u8 sx = 0; sx < scale; sx++) {
                        rectStereo(
                            cx + col * scale + sx,
                            y0 + row * scale + sy,
                            1,
                            1,
                            depth,
                            r,
                            g,
                            b);
                    }
                }
            }
        }
        cx += (5 * scale) + scale;
    }
}

static void drawIconArt(void) {
    /* PC monitor */
    rectStereo(48, 88, 120, 72, 70, 48, 52, 88);
    rectStereo(56, 96, 104, 56, 90, 58, 205, 178);

    /* Arrow */
    rectStereo(172, 118, 44, 16, 120, 255, 145, 48);
    rectStereo(210, 122, 12, 8, 130, 255, 145, 48);

    /* 3DS */
    rectStereo(228, 86, 124, 88, 150, 188, 44, 68);
    rectStereo(244, 98, 92, 52, 190, 82, 148, 248);
    rectStereo(256, 152, 68, 14, 160, 32, 36, 64);

    /* Wi-Fi */
    rectStereo(176, 78, 28, 8, 110, 255, 205, 85);
}

void drawSplash3D(void) {
    gfxSet3D(true);
    u8* left = (u8*)gfxGetFramebuffer(GFX_TOP, GFX_LEFT, nullptr, nullptr);
    u8* right = (u8*)gfxGetFramebuffer(GFX_TOP, GFX_RIGHT, nullptr, nullptr);
    fillEye(left, 10, 14, 34);
    fillEye(right, 10, 14, 34);

    drawIconArt();

    /* Title pops forward when 3D slider is on */
    textStereo("3DS MONITOR", 52, 28, 230, 3, 248, 252, 255);
    rectStereo(44, 54, 312, 4, 220, 255, 150, 55);
}

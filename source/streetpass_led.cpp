#include "streetpass_led.h"

#include <3ds.h>
#include <3ds/services/mcuhwc.h>
#include <3ds/os.h>
#include <string.h>

struct LedPreset {
    const char* name;
    u8 r;
    u8 g;
    u8 b;
    bool animated;
};

static const LedPreset kLedPresets[] = {
    {"Off",     0,   0,   0,   false},
    {"Blue",    0,   0,   255, false},
    {"Green",   0,   255, 0,   false},
    {"Red",     255, 0,   0,   false},
    {"Yellow",  255, 255, 0,   false},
    {"Purple",  180, 0,   255, false},
    {"Cyan",    0,   255, 255, false},
    {"White",   255, 255, 255, false},
    {"Orange",  255, 128, 0,   false},
    {"Pink",    255, 64,  128, false},
    {"Rainbow", 0,   0,   0,   true},
};

static const int kLedPresetCount = sizeof(kLedPresets) / sizeof(kLedPresets[0]);

static bool s_ledReady = false;
static int s_colorIndex = 1;
static u64 s_lastRainbowStep = 0;
static u16 s_rainbowHue = 0;

static void hsvToRgb(u16 hue, u8* r, u8* g, u8* b) {
    u16 h = hue % 360;
    u8 region = (u8)(h / 60);
    u8 remainder = (u8)((h % 60) * 255 / 60);

    switch (region) {
    case 0: *r = 255; *g = remainder; *b = 0; break;
    case 1: *r = 255 - remainder; *g = 255; *b = 0; break;
    case 2: *r = 0; *g = 255; *b = remainder; break;
    case 3: *r = 0; *g = 255 - remainder; *b = 255; break;
    case 4: *r = remainder; *g = 0; *b = 255; break;
    default: *r = 255; *g = 0; *b = 255 - remainder; break;
    }
}

static void applyRgb(u8 r, u8 g, u8 b) {
    if (!s_ledReady)
        return;

    InfoLedPattern pattern;
    memset(&pattern, 0, sizeof(pattern));
    pattern.delay = 0x02;
    pattern.smoothing = 0;
    pattern.loopDelay = 0;
    pattern.blinkSpeed = 0;

    for (int i = 0; i < 32; i++) {
        pattern.redPattern[i] = r;
        pattern.greenPattern[i] = g;
        pattern.bluePattern[i] = b;
    }

    MCUHWC_SetInfoLedPattern(&pattern);
}

static void applyPreset(int index) {
    if (index < 0 || index >= kLedPresetCount)
        return;

    const LedPreset* preset = &kLedPresets[index];
    if (preset->animated) {
        u8 r, g, b;
        hsvToRgb(s_rainbowHue, &r, &g, &b);
        applyRgb(r, g, b);
    } else {
        applyRgb(preset->r, preset->g, preset->b);
    }
}

bool streetpassLedInit(void) {
    if (R_SUCCEEDED(mcuHwcInit())) {
        s_ledReady = true;
        s_colorIndex = 1;
        s_rainbowHue = 0;
        s_lastRainbowStep = osGetTime();
        applyPreset(s_colorIndex);
        return true;
    }
    s_ledReady = false;
    return false;
}

void streetpassLedExit(void) {
    if (s_ledReady) {
        streetpassLedSetOff();
        mcuHwcExit();
        s_ledReady = false;
    }
}

void streetpassLedSetOff(void) {
    applyRgb(0, 0, 0);
}

int streetpassLedGetColorCount(void) {
    return kLedPresetCount;
}

int streetpassLedGetColorIndex(void) {
    return s_colorIndex;
}

const char* streetpassLedGetColorName(int index) {
    if (index < 0 || index >= kLedPresetCount)
        return "?";
    return kLedPresets[index].name;
}

void streetpassLedNextColor(void) {
    s_colorIndex = (s_colorIndex + 1) % kLedPresetCount;
    applyPreset(s_colorIndex);
}

void streetpassLedPrevColor(void) {
    s_colorIndex = (s_colorIndex + kLedPresetCount - 1) % kLedPresetCount;
    applyPreset(s_colorIndex);
}

void streetpassLedUpdate(void) {
    if (!s_ledReady || !kLedPresets[s_colorIndex].animated)
        return;

    u64 now = osGetTime();
    if (now - s_lastRainbowStep < 250000000ULL)
        return;

    s_lastRainbowStep = now;
    s_rainbowHue = (s_rainbowHue + 24) % 360;
    applyPreset(s_colorIndex);
}

bool streetpassLedIsAvailable(void) {
    return s_ledReady;
}

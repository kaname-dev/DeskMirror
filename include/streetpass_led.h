#pragma once

#include <3ds/types.h>

bool streetpassLedInit(void);
void streetpassLedExit(void);
void streetpassLedSetOff(void);

int streetpassLedGetColorCount(void);
int streetpassLedGetColorIndex(void);
const char* streetpassLedGetColorName(int index);

void streetpassLedNextColor(void);
void streetpassLedPrevColor(void);
void streetpassLedUpdate(void);

bool streetpassLedIsAvailable(void);

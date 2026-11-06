#pragma once
#include <stdint.h>
#include <stdio.h>
#include <string.h>
using PGM_P = const char*;
#define PSTR(text) text
#define pgm_read_byte(pointer) (*reinterpret_cast<const uint8_t*>(pointer))
#define strncpy_P strncpy
#define snprintf_P snprintf
#define vsnprintf_P vsnprintf

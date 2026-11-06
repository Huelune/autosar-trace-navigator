#ifndef LARGE_STD_TYPES_H
#define LARGE_STD_TYPES_H
#include <stdint.h>
typedef uint8_t uint8;
typedef uint16_t uint16;
typedef uint8 Std_ReturnType;
#define E_OK ((Std_ReturnType)0u)
#define E_NOT_OK ((Std_ReturnType)1u)
#define SENSOR_TO_UNIT(raw) ((raw) / 10)
enum { MODE_NORMAL = 1, MODE_ACTIVE = 2, MODE_FAULT = 3 };
#endif

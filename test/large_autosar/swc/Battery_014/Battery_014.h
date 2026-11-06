#ifndef BATTERY_014_H
#define BATTERY_014_H
#include "../../shared/Std_Types.h"
void Battery_014_10ms(void);
void Battery_014_Producer(void);
uint16 Battery_014_AcquireRaw(void);
uint8 Battery_014_AcquireDemand(void);
int Battery_014_Evaluate(void);
int Battery_014_Decide(void);
int Battery_014_Eligible(void);
int Battery_014_Validated(void);
int Battery_014_Decode(void);
int Battery_014_Read(void);
int Battery_014_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

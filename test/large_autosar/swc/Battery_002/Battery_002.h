#ifndef BATTERY_002_H
#define BATTERY_002_H
#include "../../shared/Std_Types.h"
void Battery_002_10ms(void);
void Battery_002_Producer(void);
uint16 Battery_002_AcquireRaw(void);
uint8 Battery_002_AcquireDemand(void);
int Battery_002_Evaluate(void);
int Battery_002_Decide(void);
int Battery_002_Eligible(void);
int Battery_002_Validated(void);
int Battery_002_Decode(void);
int Battery_002_Read(void);
int Battery_002_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

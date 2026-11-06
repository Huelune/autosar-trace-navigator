#ifndef LIGHTING_016_H
#define LIGHTING_016_H
#include "../../shared/Std_Types.h"
void Lighting_016_10ms(void);
void Lighting_016_Producer(void);
uint16 Lighting_016_AcquireRaw(void);
uint8 Lighting_016_AcquireDemand(void);
int Lighting_016_Evaluate(void);
int Lighting_016_Decide(void);
int Lighting_016_Eligible(void);
int Lighting_016_Validated(void);
int Lighting_016_Decode(void);
int Lighting_016_Read(void);
int Lighting_016_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

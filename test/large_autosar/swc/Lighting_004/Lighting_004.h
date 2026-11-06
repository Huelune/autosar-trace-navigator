#ifndef LIGHTING_004_H
#define LIGHTING_004_H
#include "../../shared/Std_Types.h"
void Lighting_004_10ms(void);
void Lighting_004_Producer(void);
uint16 Lighting_004_AcquireRaw(void);
uint8 Lighting_004_AcquireDemand(void);
int Lighting_004_Evaluate(void);
int Lighting_004_Decide(void);
int Lighting_004_Eligible(void);
int Lighting_004_Validated(void);
int Lighting_004_Decode(void);
int Lighting_004_Read(void);
int Lighting_004_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

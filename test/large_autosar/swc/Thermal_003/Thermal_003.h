#ifndef THERMAL_003_H
#define THERMAL_003_H
#include "../../shared/Std_Types.h"
void Thermal_003_10ms(void);
void Thermal_003_Producer(void);
uint16 Thermal_003_AcquireRaw(void);
uint8 Thermal_003_AcquireDemand(void);
int Thermal_003_Evaluate(void);
int Thermal_003_Decide(void);
int Thermal_003_Eligible(void);
int Thermal_003_Validated(void);
int Thermal_003_Decode(void);
int Thermal_003_Read(void);
int Thermal_003_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

#ifndef THERMAL_015_H
#define THERMAL_015_H
#include "../../shared/Std_Types.h"
void Thermal_015_10ms(void);
void Thermal_015_Producer(void);
uint16 Thermal_015_AcquireRaw(void);
uint8 Thermal_015_AcquireDemand(void);
int Thermal_015_Evaluate(void);
int Thermal_015_Decide(void);
int Thermal_015_Eligible(void);
int Thermal_015_Validated(void);
int Thermal_015_Decode(void);
int Thermal_015_Read(void);
int Thermal_015_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

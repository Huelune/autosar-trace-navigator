#ifndef CHARGING_023_H
#define CHARGING_023_H
#include "../../shared/Std_Types.h"
void Charging_023_10ms(void);
void Charging_023_Producer(void);
uint16 Charging_023_AcquireRaw(void);
uint8 Charging_023_AcquireDemand(void);
int Charging_023_Evaluate(void);
int Charging_023_Decide(void);
int Charging_023_Eligible(void);
int Charging_023_Validated(void);
int Charging_023_Decode(void);
int Charging_023_Read(void);
int Charging_023_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

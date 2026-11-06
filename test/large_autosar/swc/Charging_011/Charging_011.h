#ifndef CHARGING_011_H
#define CHARGING_011_H
#include "../../shared/Std_Types.h"
void Charging_011_10ms(void);
void Charging_011_Producer(void);
uint16 Charging_011_AcquireRaw(void);
uint8 Charging_011_AcquireDemand(void);
int Charging_011_Evaluate(void);
int Charging_011_Decide(void);
int Charging_011_Eligible(void);
int Charging_011_Validated(void);
int Charging_011_Decode(void);
int Charging_011_Read(void);
int Charging_011_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

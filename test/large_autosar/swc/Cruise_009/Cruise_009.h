#ifndef CRUISE_009_H
#define CRUISE_009_H
#include "../../shared/Std_Types.h"
void Cruise_009_10ms(void);
void Cruise_009_Producer(void);
uint16 Cruise_009_AcquireRaw(void);
uint8 Cruise_009_AcquireDemand(void);
int Cruise_009_Evaluate(void);
int Cruise_009_Decide(void);
int Cruise_009_Eligible(void);
int Cruise_009_Validated(void);
int Cruise_009_Decode(void);
int Cruise_009_Read(void);
int Cruise_009_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

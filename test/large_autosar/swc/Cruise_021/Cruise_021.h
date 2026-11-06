#ifndef CRUISE_021_H
#define CRUISE_021_H
#include "../../shared/Std_Types.h"
void Cruise_021_10ms(void);
void Cruise_021_Producer(void);
uint16 Cruise_021_AcquireRaw(void);
uint8 Cruise_021_AcquireDemand(void);
int Cruise_021_Evaluate(void);
int Cruise_021_Decide(void);
int Cruise_021_Eligible(void);
int Cruise_021_Validated(void);
int Cruise_021_Decode(void);
int Cruise_021_Read(void);
int Cruise_021_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

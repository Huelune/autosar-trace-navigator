#ifndef DOOR_005_H
#define DOOR_005_H
#include "../../shared/Std_Types.h"
void Door_005_10ms(void);
void Door_005_Producer(void);
uint16 Door_005_AcquireRaw(void);
uint8 Door_005_AcquireDemand(void);
int Door_005_Evaluate(void);
int Door_005_Decide(void);
int Door_005_Eligible(void);
int Door_005_Validated(void);
int Door_005_Decode(void);
int Door_005_Read(void);
int Door_005_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

#ifndef DOOR_017_H
#define DOOR_017_H
#include "../../shared/Std_Types.h"
void Door_017_10ms(void);
void Door_017_Producer(void);
uint16 Door_017_AcquireRaw(void);
uint8 Door_017_AcquireDemand(void);
int Door_017_Evaluate(void);
int Door_017_Decide(void);
int Door_017_Eligible(void);
int Door_017_Validated(void);
int Door_017_Decode(void);
int Door_017_Read(void);
int Door_017_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

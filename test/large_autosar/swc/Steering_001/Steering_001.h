#ifndef STEERING_001_H
#define STEERING_001_H
#include "../../shared/Std_Types.h"
void Steering_001_10ms(void);
void Steering_001_Producer(void);
uint16 Steering_001_AcquireRaw(void);
uint8 Steering_001_AcquireDemand(void);
int Steering_001_Evaluate(void);
int Steering_001_Decide(void);
int Steering_001_Eligible(void);
int Steering_001_Validated(void);
int Steering_001_Decode(void);
int Steering_001_Read(void);
int Steering_001_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

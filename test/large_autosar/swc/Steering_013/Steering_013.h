#ifndef STEERING_013_H
#define STEERING_013_H
#include "../../shared/Std_Types.h"
void Steering_013_10ms(void);
void Steering_013_Producer(void);
uint16 Steering_013_AcquireRaw(void);
uint8 Steering_013_AcquireDemand(void);
int Steering_013_Evaluate(void);
int Steering_013_Decide(void);
int Steering_013_Eligible(void);
int Steering_013_Validated(void);
int Steering_013_Decode(void);
int Steering_013_Read(void);
int Steering_013_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

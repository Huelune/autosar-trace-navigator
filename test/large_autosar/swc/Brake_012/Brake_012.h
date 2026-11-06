#ifndef BRAKE_012_H
#define BRAKE_012_H
#include "../../shared/Std_Types.h"
void Brake_012_10ms(void);
void Brake_012_Producer(void);
uint16 Brake_012_AcquireRaw(void);
uint8 Brake_012_AcquireDemand(void);
int Brake_012_Evaluate(void);
int Brake_012_Decide(void);
int Brake_012_Eligible(void);
int Brake_012_Validated(void);
int Brake_012_Decode(void);
int Brake_012_Read(void);
int Brake_012_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

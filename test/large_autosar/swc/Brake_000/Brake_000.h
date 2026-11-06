#ifndef BRAKE_000_H
#define BRAKE_000_H
#include "../../shared/Std_Types.h"
void Brake_000_10ms(void);
void Brake_000_Producer(void);
uint16 Brake_000_AcquireRaw(void);
uint8 Brake_000_AcquireDemand(void);
int Brake_000_Evaluate(void);
int Brake_000_Decide(void);
int Brake_000_Eligible(void);
int Brake_000_Validated(void);
int Brake_000_Decode(void);
int Brake_000_Read(void);
int Brake_000_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

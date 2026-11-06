#ifndef WIPER_007_H
#define WIPER_007_H
#include "../../shared/Std_Types.h"
void Wiper_007_10ms(void);
void Wiper_007_Producer(void);
uint16 Wiper_007_AcquireRaw(void);
uint8 Wiper_007_AcquireDemand(void);
int Wiper_007_Evaluate(void);
int Wiper_007_Decide(void);
int Wiper_007_Eligible(void);
int Wiper_007_Validated(void);
int Wiper_007_Decode(void);
int Wiper_007_Read(void);
int Wiper_007_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

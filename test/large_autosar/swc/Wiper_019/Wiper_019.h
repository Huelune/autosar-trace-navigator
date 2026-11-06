#ifndef WIPER_019_H
#define WIPER_019_H
#include "../../shared/Std_Types.h"
void Wiper_019_10ms(void);
void Wiper_019_Producer(void);
uint16 Wiper_019_AcquireRaw(void);
uint8 Wiper_019_AcquireDemand(void);
int Wiper_019_Evaluate(void);
int Wiper_019_Decide(void);
int Wiper_019_Eligible(void);
int Wiper_019_Validated(void);
int Wiper_019_Decode(void);
int Wiper_019_Read(void);
int Wiper_019_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

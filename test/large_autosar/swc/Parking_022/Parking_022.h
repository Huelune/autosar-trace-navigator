#ifndef PARKING_022_H
#define PARKING_022_H
#include "../../shared/Std_Types.h"
void Parking_022_10ms(void);
void Parking_022_Producer(void);
uint16 Parking_022_AcquireRaw(void);
uint8 Parking_022_AcquireDemand(void);
int Parking_022_Evaluate(void);
int Parking_022_Decide(void);
int Parking_022_Eligible(void);
int Parking_022_Validated(void);
int Parking_022_Decode(void);
int Parking_022_Read(void);
int Parking_022_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

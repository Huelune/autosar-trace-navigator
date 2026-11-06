#ifndef PARKING_010_H
#define PARKING_010_H
#include "../../shared/Std_Types.h"
void Parking_010_10ms(void);
void Parking_010_Producer(void);
uint16 Parking_010_AcquireRaw(void);
uint8 Parking_010_AcquireDemand(void);
int Parking_010_Evaluate(void);
int Parking_010_Decide(void);
int Parking_010_Eligible(void);
int Parking_010_Validated(void);
int Parking_010_Decode(void);
int Parking_010_Read(void);
int Parking_010_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

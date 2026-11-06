#ifndef SEAT_018_H
#define SEAT_018_H
#include "../../shared/Std_Types.h"
void Seat_018_10ms(void);
void Seat_018_Producer(void);
uint16 Seat_018_AcquireRaw(void);
uint8 Seat_018_AcquireDemand(void);
int Seat_018_Evaluate(void);
int Seat_018_Decide(void);
int Seat_018_Eligible(void);
int Seat_018_Validated(void);
int Seat_018_Decode(void);
int Seat_018_Read(void);
int Seat_018_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

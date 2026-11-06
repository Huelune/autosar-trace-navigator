#ifndef SEAT_006_H
#define SEAT_006_H
#include "../../shared/Std_Types.h"
void Seat_006_10ms(void);
void Seat_006_Producer(void);
uint16 Seat_006_AcquireRaw(void);
uint8 Seat_006_AcquireDemand(void);
int Seat_006_Evaluate(void);
int Seat_006_Decide(void);
int Seat_006_Eligible(void);
int Seat_006_Validated(void);
int Seat_006_Decode(void);
int Seat_006_Read(void);
int Seat_006_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

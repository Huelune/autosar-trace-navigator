#ifndef BRAKE_CONTROL_H
#define BRAKE_CONTROL_H

#include "Std_Types.h"

typedef enum {
    BRAKE_NORMAL = 1,
    BRAKE_ASSIST = 2,
    BRAKE_FAULT = 3
} BrakeMode;

void BrakeControl_10ms(void);
BrakeMode EvaluateBrakeMode(void);
int IsAssistRequested(void);
int IsSpeedEligible(void);
int GetValidatedSpeed(void);
int DecodeSpeed(void);
int ReadRawSpeed(void);
void SensorAcquisition_10ms(void);

#endif

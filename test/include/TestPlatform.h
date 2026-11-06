#ifndef TEST_PLATFORM_H
#define TEST_PLATFORM_H

#include "Std_Types.h"

uint16 IoHwAb_ReadSpeedRaw(void);
uint8 IoHwAb_ReadPedalPercent(void);
void TestPlatform_Reset(uint16 speed, uint8 pedal,
                        Std_ReturnType speed_status,
                        Std_ReturnType pedal_status);
uint8 TestPlatform_LastMode(void);
unsigned int TestPlatform_ModeWrites(void);

#endif

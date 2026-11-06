#include "BrakeControl.h"
#include "Rte_SensorAcquisition.h"
#include "TestPlatform.h"

void SensorAcquisition_10ms(void)
{
    uint16 speed = IoHwAb_ReadSpeedRaw();
    uint8 pedal = IoHwAb_ReadPedalPercent();

    (void)Rte_Write_Speed_Raw(speed);
    (void)Rte_Write_Pedal_Percent(pedal);
}

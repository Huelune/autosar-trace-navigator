#include "Steering_001.h"
#include "Rte_Steering_001.h"
void Steering_001_Producer(void)
{
    (void)Rte_Write_Steering_001_Signal_Raw(Steering_001_AcquireRaw());
    (void)Rte_Write_Steering_001_Demand_Percent(Steering_001_AcquireDemand());
}
uint16 Steering_001_AcquireRaw(void) { return Platform_ReadRaw(1u); }
uint8 Steering_001_AcquireDemand(void) { return Platform_ReadDemand(1u); }

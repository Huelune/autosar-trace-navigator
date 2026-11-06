#include "Steering_013.h"
#include "Rte_Steering_013.h"
void Steering_013_Producer(void)
{
    (void)Rte_Write_Steering_013_Signal_Raw(Steering_013_AcquireRaw());
    (void)Rte_Write_Steering_013_Demand_Percent(Steering_013_AcquireDemand());
}
uint16 Steering_013_AcquireRaw(void) { return Platform_ReadRaw(13u); }
uint8 Steering_013_AcquireDemand(void) { return Platform_ReadDemand(13u); }

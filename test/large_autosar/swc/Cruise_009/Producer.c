#include "Cruise_009.h"
#include "Rte_Cruise_009.h"
void Cruise_009_Producer(void)
{
    (void)Rte_Write_Cruise_009_Signal_Raw(Cruise_009_AcquireRaw());
    (void)Rte_Write_Cruise_009_Demand_Percent(Cruise_009_AcquireDemand());
}
uint16 Cruise_009_AcquireRaw(void) { return Platform_ReadRaw(9u); }
uint8 Cruise_009_AcquireDemand(void) { return Platform_ReadDemand(9u); }

#include "Cruise_021.h"
#include "Rte_Cruise_021.h"
void Cruise_021_Producer(void)
{
    (void)Rte_Write_Cruise_021_Signal_Raw(Cruise_021_AcquireRaw());
    (void)Rte_Write_Cruise_021_Demand_Percent(Cruise_021_AcquireDemand());
}
uint16 Cruise_021_AcquireRaw(void) { return Platform_ReadRaw(21u); }
uint8 Cruise_021_AcquireDemand(void) { return Platform_ReadDemand(21u); }

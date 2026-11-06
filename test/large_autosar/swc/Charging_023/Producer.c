#include "Charging_023.h"
#include "Rte_Charging_023.h"
void Charging_023_Producer(void)
{
    (void)Rte_Write_Charging_023_Signal_Raw(Charging_023_AcquireRaw());
    (void)Rte_Write_Charging_023_Demand_Percent(Charging_023_AcquireDemand());
}
uint16 Charging_023_AcquireRaw(void) { return Platform_ReadRaw(23u); }
uint8 Charging_023_AcquireDemand(void) { return Platform_ReadDemand(23u); }

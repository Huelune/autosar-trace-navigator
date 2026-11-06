#include "Charging_011.h"
#include "Rte_Charging_011.h"
void Charging_011_Producer(void)
{
    (void)Rte_Write_Charging_011_Signal_Raw(Charging_011_AcquireRaw());
    (void)Rte_Write_Charging_011_Demand_Percent(Charging_011_AcquireDemand());
}
uint16 Charging_011_AcquireRaw(void) { return Platform_ReadRaw(11u); }
uint8 Charging_011_AcquireDemand(void) { return Platform_ReadDemand(11u); }

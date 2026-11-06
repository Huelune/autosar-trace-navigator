#include "Thermal_015.h"
#include "Rte_Thermal_015.h"
void Thermal_015_Producer(void)
{
    (void)Rte_Write_Thermal_015_Signal_Raw(Thermal_015_AcquireRaw());
    (void)Rte_Write_Thermal_015_Demand_Percent(Thermal_015_AcquireDemand());
}
uint16 Thermal_015_AcquireRaw(void) { return Platform_ReadRaw(15u); }
uint8 Thermal_015_AcquireDemand(void) { return Platform_ReadDemand(15u); }

#include "Thermal_003.h"
#include "Rte_Thermal_003.h"
void Thermal_003_Producer(void)
{
    (void)Rte_Write_Thermal_003_Signal_Raw(Thermal_003_AcquireRaw());
    (void)Rte_Write_Thermal_003_Demand_Percent(Thermal_003_AcquireDemand());
}
uint16 Thermal_003_AcquireRaw(void) { return Platform_ReadRaw(3u); }
uint8 Thermal_003_AcquireDemand(void) { return Platform_ReadDemand(3u); }

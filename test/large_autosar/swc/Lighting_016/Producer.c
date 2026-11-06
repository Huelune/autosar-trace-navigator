#include "Lighting_016.h"
#include "Rte_Lighting_016.h"
void Lighting_016_Producer(void)
{
    (void)Rte_Write_Lighting_016_Signal_Raw(Lighting_016_AcquireRaw());
    (void)Rte_Write_Lighting_016_Demand_Percent(Lighting_016_AcquireDemand());
}
uint16 Lighting_016_AcquireRaw(void) { return Platform_ReadRaw(16u); }
uint8 Lighting_016_AcquireDemand(void) { return Platform_ReadDemand(16u); }

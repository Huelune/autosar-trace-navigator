#include "Lighting_004.h"
#include "Rte_Lighting_004.h"
void Lighting_004_Producer(void)
{
    (void)Rte_Write_Lighting_004_Signal_Raw(Lighting_004_AcquireRaw());
    (void)Rte_Write_Lighting_004_Demand_Percent(Lighting_004_AcquireDemand());
}
uint16 Lighting_004_AcquireRaw(void) { return Platform_ReadRaw(4u); }
uint8 Lighting_004_AcquireDemand(void) { return Platform_ReadDemand(4u); }

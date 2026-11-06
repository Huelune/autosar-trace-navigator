#include "Door_005.h"
#include "Rte_Door_005.h"
void Door_005_Producer(void)
{
    (void)Rte_Write_Door_005_Signal_Raw(Door_005_AcquireRaw());
    (void)Rte_Write_Door_005_Demand_Percent(Door_005_AcquireDemand());
}
uint16 Door_005_AcquireRaw(void) { return Platform_ReadRaw(5u); }
uint8 Door_005_AcquireDemand(void) { return Platform_ReadDemand(5u); }

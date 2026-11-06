#include "Door_017.h"
#include "Rte_Door_017.h"
void Door_017_Producer(void)
{
    (void)Rte_Write_Door_017_Signal_Raw(Door_017_AcquireRaw());
    (void)Rte_Write_Door_017_Demand_Percent(Door_017_AcquireDemand());
}
uint16 Door_017_AcquireRaw(void) { return Platform_ReadRaw(17u); }
uint8 Door_017_AcquireDemand(void) { return Platform_ReadDemand(17u); }

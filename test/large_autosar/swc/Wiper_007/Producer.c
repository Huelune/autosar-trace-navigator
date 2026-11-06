#include "Wiper_007.h"
#include "Rte_Wiper_007.h"
void Wiper_007_Producer(void)
{
    (void)Rte_Write_Wiper_007_Signal_Raw(Wiper_007_AcquireRaw());
    (void)Rte_Write_Wiper_007_Demand_Percent(Wiper_007_AcquireDemand());
}
uint16 Wiper_007_AcquireRaw(void) { return Platform_ReadRaw(7u); }
uint8 Wiper_007_AcquireDemand(void) { return Platform_ReadDemand(7u); }

#include "Wiper_019.h"
#include "Rte_Wiper_019.h"
void Wiper_019_Producer(void)
{
    (void)Rte_Write_Wiper_019_Signal_Raw(Wiper_019_AcquireRaw());
    (void)Rte_Write_Wiper_019_Demand_Percent(Wiper_019_AcquireDemand());
}
uint16 Wiper_019_AcquireRaw(void) { return Platform_ReadRaw(19u); }
uint8 Wiper_019_AcquireDemand(void) { return Platform_ReadDemand(19u); }

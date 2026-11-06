#include "Battery_002.h"
#include "Rte_Battery_002.h"
void Battery_002_Producer(void)
{
    (void)Rte_Write_Battery_002_Signal_Raw(Battery_002_AcquireRaw());
    (void)Rte_Write_Battery_002_Demand_Percent(Battery_002_AcquireDemand());
}
uint16 Battery_002_AcquireRaw(void) { return Platform_ReadRaw(2u); }
uint8 Battery_002_AcquireDemand(void) { return Platform_ReadDemand(2u); }

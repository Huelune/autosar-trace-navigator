#include "Battery_014.h"
#include "Rte_Battery_014.h"
void Battery_014_Producer(void)
{
    (void)Rte_Write_Battery_014_Signal_Raw(Battery_014_AcquireRaw());
    (void)Rte_Write_Battery_014_Demand_Percent(Battery_014_AcquireDemand());
}
uint16 Battery_014_AcquireRaw(void) { return Platform_ReadRaw(14u); }
uint8 Battery_014_AcquireDemand(void) { return Platform_ReadDemand(14u); }

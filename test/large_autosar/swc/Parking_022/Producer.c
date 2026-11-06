#include "Parking_022.h"
#include "Rte_Parking_022.h"
void Parking_022_Producer(void)
{
    (void)Rte_Write_Parking_022_Signal_Raw(Parking_022_AcquireRaw());
    (void)Rte_Write_Parking_022_Demand_Percent(Parking_022_AcquireDemand());
}
uint16 Parking_022_AcquireRaw(void) { return Platform_ReadRaw(22u); }
uint8 Parking_022_AcquireDemand(void) { return Platform_ReadDemand(22u); }

#include "Parking_010.h"
#include "Rte_Parking_010.h"
void Parking_010_Producer(void)
{
    (void)Rte_Write_Parking_010_Signal_Raw(Parking_010_AcquireRaw());
    (void)Rte_Write_Parking_010_Demand_Percent(Parking_010_AcquireDemand());
}
uint16 Parking_010_AcquireRaw(void) { return Platform_ReadRaw(10u); }
uint8 Parking_010_AcquireDemand(void) { return Platform_ReadDemand(10u); }

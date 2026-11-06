#include "Seat_006.h"
#include "Rte_Seat_006.h"
void Seat_006_Producer(void)
{
    (void)Rte_Write_Seat_006_Signal_Raw(Seat_006_AcquireRaw());
    (void)Rte_Write_Seat_006_Demand_Percent(Seat_006_AcquireDemand());
}
uint16 Seat_006_AcquireRaw(void) { return Platform_ReadRaw(6u); }
uint8 Seat_006_AcquireDemand(void) { return Platform_ReadDemand(6u); }

void Seat_006_BackupProducer(void)
{
    (void)Rte_Write_Seat_006_Signal_Raw(0u);
}

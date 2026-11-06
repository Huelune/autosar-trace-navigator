#include "Seat_018.h"
#include "Rte_Seat_018.h"
void Seat_018_Producer(void)
{
    (void)Rte_Write_Seat_018_Signal_Raw(Seat_018_AcquireRaw());
    (void)Rte_Write_Seat_018_Demand_Percent(Seat_018_AcquireDemand());
}
uint16 Seat_018_AcquireRaw(void) { return Platform_ReadRaw(18u); }
uint8 Seat_018_AcquireDemand(void) { return Platform_ReadDemand(18u); }

void Seat_018_BackupProducer(void)
{
    (void)Rte_Write_Seat_018_Signal_Raw(0u);
}

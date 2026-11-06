#include "Brake_000.h"
#include "Rte_Brake_000.h"
void Brake_000_Producer(void)
{
    (void)Rte_Write_Brake_000_Signal_Raw(Brake_000_AcquireRaw());
    (void)Rte_Write_Brake_000_Demand_Percent(Brake_000_AcquireDemand());
}
uint16 Brake_000_AcquireRaw(void) { return Platform_ReadRaw(0u); }
uint8 Brake_000_AcquireDemand(void) { return Platform_ReadDemand(0u); }

void Brake_000_BackupProducer(void)
{
    (void)Rte_Write_Brake_000_Signal_Raw(0u);
}

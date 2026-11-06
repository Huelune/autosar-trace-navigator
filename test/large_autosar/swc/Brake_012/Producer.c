#include "Brake_012.h"
#include "Rte_Brake_012.h"
void Brake_012_Producer(void)
{
    (void)Rte_Write_Brake_012_Signal_Raw(Brake_012_AcquireRaw());
    (void)Rte_Write_Brake_012_Demand_Percent(Brake_012_AcquireDemand());
}
uint16 Brake_012_AcquireRaw(void) { return Platform_ReadRaw(12u); }
uint8 Brake_012_AcquireDemand(void) { return Platform_ReadDemand(12u); }

void Brake_012_BackupProducer(void)
{
    (void)Rte_Write_Brake_012_Signal_Raw(0u);
}

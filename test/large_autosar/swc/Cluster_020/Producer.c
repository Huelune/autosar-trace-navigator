#include "Cluster_020.h"
#include "Rte_Cluster_020.h"
void Cluster_020_Producer(void)
{
    (void)Rte_Write_Cluster_020_Signal_Raw(Cluster_020_AcquireRaw());
    (void)Rte_Write_Cluster_020_Demand_Percent(Cluster_020_AcquireDemand());
}
uint16 Cluster_020_AcquireRaw(void) { return Platform_ReadRaw(20u); }
uint8 Cluster_020_AcquireDemand(void) { return Platform_ReadDemand(20u); }

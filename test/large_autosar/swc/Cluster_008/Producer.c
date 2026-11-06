#include "Cluster_008.h"
#include "Rte_Cluster_008.h"
void Cluster_008_Producer(void)
{
    (void)Rte_Write_Cluster_008_Signal_Raw(Cluster_008_AcquireRaw());
    (void)Rte_Write_Cluster_008_Demand_Percent(Cluster_008_AcquireDemand());
}
uint16 Cluster_008_AcquireRaw(void) { return Platform_ReadRaw(8u); }
uint8 Cluster_008_AcquireDemand(void) { return Platform_ReadDemand(8u); }

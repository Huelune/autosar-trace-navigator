#include "Cluster_008.h"
#include "Rte_Cluster_008.h"
int Cluster_008_Decide(void)
{
    int eligible = Cluster_008_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Cluster_008_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Cluster_008_Eligible(void)
{
    int value = Cluster_008_Validated();
    if (value < 0) return -1;
    else if (value >= 35) return 1;
    else return 0;
}

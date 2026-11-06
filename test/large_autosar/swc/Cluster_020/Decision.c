#include "Cluster_020.h"
#include "Rte_Cluster_020.h"
int Cluster_020_Decide(void)
{
    int eligible = Cluster_020_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Cluster_020_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Cluster_020_Eligible(void)
{
    int value = Cluster_020_Validated();
    if (value < 0) return -1;
    else if (value >= 20) return 1;
    else return 0;
}

#include "Steering_001.h"
#include "Rte_Steering_001.h"
int Steering_001_Decide(void)
{
    int eligible = Steering_001_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Steering_001_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Steering_001_Eligible(void)
{
    int value = Steering_001_Validated();
    if (value < 0) return -1;
    else if (value >= 25) return 1;
    else return 0;
}

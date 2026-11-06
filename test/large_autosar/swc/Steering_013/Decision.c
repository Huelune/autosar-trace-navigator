#include "Steering_013.h"
#include "Rte_Steering_013.h"
int Steering_013_Decide(void)
{
    int eligible = Steering_013_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Steering_013_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Steering_013_Eligible(void)
{
    int value = Steering_013_Validated();
    if (value < 0) return -1;
    else if (value >= 35) return 1;
    else return 0;
}

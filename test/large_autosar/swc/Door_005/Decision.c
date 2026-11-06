#include "Door_005.h"
#include "Rte_Door_005.h"
int Door_005_Decide(void)
{
    int eligible = Door_005_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Door_005_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Door_005_Eligible(void)
{
    int value = Door_005_Validated();
    if (value < 0) return -1;
    else if (value >= 20) return 1;
    else return 0;
}

#include "Door_017.h"
#include "Rte_Door_017.h"
int Door_017_Decide(void)
{
    int eligible = Door_017_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Door_017_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Door_017_Eligible(void)
{
    int value = Door_017_Validated();
    if (value < 0) return -1;
    else if (value >= 30) return 1;
    else return 0;
}

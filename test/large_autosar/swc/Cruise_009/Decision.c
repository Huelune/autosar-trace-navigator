#include "Cruise_009.h"
#include "Rte_Cruise_009.h"
int Cruise_009_Decide(void)
{
    int eligible = Cruise_009_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Cruise_009_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Cruise_009_Eligible(void)
{
    int value = Cruise_009_Validated();
    if (value < 0) return -1;
    else if (value >= 40) return 1;
    else return 0;
}

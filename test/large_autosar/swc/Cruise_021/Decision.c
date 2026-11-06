#include "Cruise_021.h"
#include "Rte_Cruise_021.h"
int Cruise_021_Decide(void)
{
    int eligible = Cruise_021_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Cruise_021_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Cruise_021_Eligible(void)
{
    int value = Cruise_021_Validated();
    if (value < 0) return -1;
    else if (value >= 25) return 1;
    else return 0;
}

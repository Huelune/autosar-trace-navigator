#include "Charging_023.h"
#include "Rte_Charging_023.h"
int Charging_023_Decide(void)
{
    int eligible = Charging_023_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Charging_023_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Charging_023_Eligible(void)
{
    int value = Charging_023_Validated();
    if (value < 0) return -1;
    else if (value >= 35) return 1;
    else return 0;
}

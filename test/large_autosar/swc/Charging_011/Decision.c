#include "Charging_011.h"
#include "Rte_Charging_011.h"
int Charging_011_Decide(void)
{
    int eligible = Charging_011_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Charging_011_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Charging_011_Eligible(void)
{
    int value = Charging_011_Validated();
    if (value < 0) return -1;
    else if (value >= 25) return 1;
    else return 0;
}

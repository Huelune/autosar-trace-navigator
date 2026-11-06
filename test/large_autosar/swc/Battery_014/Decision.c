#include "Battery_014.h"
#include "Rte_Battery_014.h"
int Battery_014_Decide(void)
{
    int eligible = Battery_014_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Battery_014_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Battery_014_Eligible(void)
{
    int value = Battery_014_Validated();
    if (value < 0) return -1;
    else if (value >= 40) return 1;
    else return 0;
}

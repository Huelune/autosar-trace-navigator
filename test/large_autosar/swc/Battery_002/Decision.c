#include "Battery_002.h"
#include "Rte_Battery_002.h"
int Battery_002_Decide(void)
{
    int eligible = Battery_002_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Battery_002_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Battery_002_Eligible(void)
{
    int value = Battery_002_Validated();
    if (value < 0) return -1;
    else if (value >= 30) return 1;
    else return 0;
}

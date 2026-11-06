#include "Lighting_016.h"
#include "Rte_Lighting_016.h"
int Lighting_016_Decide(void)
{
    int eligible = Lighting_016_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Lighting_016_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Lighting_016_Eligible(void)
{
    int value = Lighting_016_Validated();
    if (value < 0) return -1;
    else if (value >= 25) return 1;
    else return 0;
}

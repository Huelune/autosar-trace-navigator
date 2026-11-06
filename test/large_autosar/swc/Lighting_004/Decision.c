#include "Lighting_004.h"
#include "Rte_Lighting_004.h"
int Lighting_004_Decide(void)
{
    int eligible = Lighting_004_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Lighting_004_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Lighting_004_Eligible(void)
{
    int value = Lighting_004_Validated();
    if (value < 0) return -1;
    else if (value >= 40) return 1;
    else return 0;
}

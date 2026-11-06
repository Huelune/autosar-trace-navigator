#include "Thermal_003.h"
#include "Rte_Thermal_003.h"
int Thermal_003_Decide(void)
{
    int eligible = Thermal_003_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Thermal_003_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Thermal_003_Eligible(void)
{
    int value = Thermal_003_Validated();
    if (value < 0) return -1;
    else if (value >= 35) return 1;
    else return 0;
}

#include "Thermal_015.h"
#include "Rte_Thermal_015.h"
int Thermal_015_Decide(void)
{
    int eligible = Thermal_015_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Thermal_015_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Thermal_015_Eligible(void)
{
    int value = Thermal_015_Validated();
    if (value < 0) return -1;
    else if (value >= 20) return 1;
    else return 0;
}

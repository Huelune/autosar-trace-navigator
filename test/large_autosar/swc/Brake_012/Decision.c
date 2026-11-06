#include "Brake_012.h"
#include "Rte_Brake_012.h"
int Brake_012_Decide(void)
{
    int eligible = Brake_012_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Brake_012_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Brake_012_Eligible(void)
{
    int value = Brake_012_Validated();
    if (value < 0) return -1;
    else if (value >= 30) return 1;
    else return 0;
}

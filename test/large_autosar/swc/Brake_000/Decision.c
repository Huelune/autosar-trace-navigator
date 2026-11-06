#include "Brake_000.h"
#include "Rte_Brake_000.h"
int Brake_000_Decide(void)
{
    int eligible = Brake_000_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Brake_000_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Brake_000_Eligible(void)
{
    int value = Brake_000_Validated();
    if (value < 0) return -1;
    else if (value >= 20) return 1;
    else return 0;
}

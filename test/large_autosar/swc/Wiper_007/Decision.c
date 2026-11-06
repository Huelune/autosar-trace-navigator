#include "Wiper_007.h"
#include "Rte_Wiper_007.h"
int Wiper_007_Decide(void)
{
    int eligible = Wiper_007_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Wiper_007_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Wiper_007_Eligible(void)
{
    int value = Wiper_007_Validated();
    if (value < 0) return -1;
    else if (value >= 30) return 1;
    else return 0;
}

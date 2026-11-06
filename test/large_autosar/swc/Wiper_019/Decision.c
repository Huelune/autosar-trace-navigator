#include "Wiper_019.h"
#include "Rte_Wiper_019.h"
int Wiper_019_Decide(void)
{
    int eligible = Wiper_019_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Wiper_019_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Wiper_019_Eligible(void)
{
    int value = Wiper_019_Validated();
    if (value < 0) return -1;
    else if (value >= 40) return 1;
    else return 0;
}

#include "Parking_022.h"
#include "Rte_Parking_022.h"
int Parking_022_Decide(void)
{
    int eligible = Parking_022_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Parking_022_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Parking_022_Eligible(void)
{
    int value = Parking_022_Validated();
    if (value < 0) return -1;
    else if (value >= 30) return 1;
    else return 0;
}

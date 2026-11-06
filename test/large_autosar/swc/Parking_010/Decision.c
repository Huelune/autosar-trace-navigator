#include "Parking_010.h"
#include "Rte_Parking_010.h"
int Parking_010_Decide(void)
{
    int eligible = Parking_010_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Parking_010_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Parking_010_Eligible(void)
{
    int value = Parking_010_Validated();
    if (value < 0) return -1;
    else if (value >= 20) return 1;
    else return 0;
}

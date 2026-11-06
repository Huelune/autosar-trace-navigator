#include "Seat_006.h"
#include "Rte_Seat_006.h"
int Seat_006_Decide(void)
{
    int eligible = Seat_006_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Seat_006_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Seat_006_Eligible(void)
{
    int value = Seat_006_Validated();
    if (value < 0) return -1;
    else if (value >= 25) return 1;
    else return 0;
}

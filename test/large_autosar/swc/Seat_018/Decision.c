#include "Seat_018.h"
#include "Rte_Seat_018.h"
int Seat_018_Decide(void)
{
    int eligible = Seat_018_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_Seat_018_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }
}
int Seat_018_Eligible(void)
{
    int value = Seat_018_Validated();
    if (value < 0) return -1;
    else if (value >= 35) return 1;
    else return 0;
}

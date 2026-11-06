#include "Charging_023.h"
#include "Rte_Charging_023.h"
void Charging_023_10ms(void)
{
    int mode = Charging_023_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Charging_023_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Charging_023_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Charging_023_Mode((uint8)MODE_NORMAL);
    }
}
int Charging_023_Evaluate(void)
{
    int request = Charging_023_Decide();
    if (request < 0) {
        (void)Charging_023_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

#include "Cruise_021.h"
#include "Rte_Cruise_021.h"
void Cruise_021_10ms(void)
{
    int mode = Cruise_021_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Cruise_021_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Cruise_021_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Cruise_021_Mode((uint8)MODE_NORMAL);
    }
}
int Cruise_021_Evaluate(void)
{
    int request = Cruise_021_Decide();
    if (request < 0) {
        (void)Cruise_021_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

#include "Cruise_009.h"
#include "Rte_Cruise_009.h"
void Cruise_009_10ms(void)
{
    int mode = Cruise_009_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Cruise_009_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Cruise_009_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Cruise_009_Mode((uint8)MODE_NORMAL);
    }
}
int Cruise_009_Evaluate(void)
{
    int request = Cruise_009_Decide();
    if (request < 0) {
        (void)Cruise_009_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

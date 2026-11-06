#include "Battery_014.h"
#include "Rte_Battery_014.h"
void Battery_014_10ms(void)
{
    int mode = Battery_014_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Battery_014_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Battery_014_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Battery_014_Mode((uint8)MODE_NORMAL);
    }
}
int Battery_014_Evaluate(void)
{
    int request = Battery_014_Decide();
    if (request < 0) {
        (void)Battery_014_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

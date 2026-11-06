#include "Battery_002.h"
#include "Rte_Battery_002.h"
void Battery_002_10ms(void)
{
    int mode = Battery_002_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Battery_002_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Battery_002_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Battery_002_Mode((uint8)MODE_NORMAL);
    }
}
int Battery_002_Evaluate(void)
{
    int request = Battery_002_Decide();
    if (request < 0) {
        (void)Battery_002_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

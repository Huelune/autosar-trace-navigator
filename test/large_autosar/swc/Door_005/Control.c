#include "Door_005.h"
#include "Rte_Door_005.h"
void Door_005_10ms(void)
{
    int mode = Door_005_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Door_005_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Door_005_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Door_005_Mode((uint8)MODE_NORMAL);
    }
}
int Door_005_Evaluate(void)
{
    int request = Door_005_Decide();
    if (request < 0) {
        (void)Door_005_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

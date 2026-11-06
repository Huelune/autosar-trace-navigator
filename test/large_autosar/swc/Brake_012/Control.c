#include "Brake_012.h"
#include "Rte_Brake_012.h"
void Brake_012_10ms(void)
{
    int mode = Brake_012_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Brake_012_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Brake_012_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Brake_012_Mode((uint8)MODE_NORMAL);
    }
}
int Brake_012_Evaluate(void)
{
    int request = Brake_012_Decide();
    if (request < 0) {
        (void)Brake_012_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

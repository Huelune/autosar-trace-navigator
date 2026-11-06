#include "Wiper_007.h"
#include "Rte_Wiper_007.h"
void Wiper_007_10ms(void)
{
    int mode = Wiper_007_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Wiper_007_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Wiper_007_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Wiper_007_Mode((uint8)MODE_NORMAL);
    }
}
int Wiper_007_Evaluate(void)
{
    int request = Wiper_007_Decide();
    if (request < 0) {
        (void)Wiper_007_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

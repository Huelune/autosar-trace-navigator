#include "Wiper_019.h"
#include "Rte_Wiper_019.h"
void Wiper_019_10ms(void)
{
    int mode = Wiper_019_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Wiper_019_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Wiper_019_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Wiper_019_Mode((uint8)MODE_NORMAL);
    }
}
int Wiper_019_Evaluate(void)
{
    int request = Wiper_019_Decide();
    if (request < 0) {
        (void)Wiper_019_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

#include "Steering_001.h"
#include "Rte_Steering_001.h"
void Steering_001_10ms(void)
{
    int mode = Steering_001_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Steering_001_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Steering_001_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Steering_001_Mode((uint8)MODE_NORMAL);
    }
}
int Steering_001_Evaluate(void)
{
    int request = Steering_001_Decide();
    if (request < 0) {
        (void)Steering_001_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

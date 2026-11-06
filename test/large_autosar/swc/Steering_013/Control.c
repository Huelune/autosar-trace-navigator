#include "Steering_013.h"
#include "Rte_Steering_013.h"
void Steering_013_10ms(void)
{
    int mode = Steering_013_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Steering_013_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Steering_013_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Steering_013_Mode((uint8)MODE_NORMAL);
    }
}
int Steering_013_Evaluate(void)
{
    int request = Steering_013_Decide();
    if (request < 0) {
        (void)Steering_013_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

#include "Parking_022.h"
#include "Rte_Parking_022.h"
void Parking_022_10ms(void)
{
    int mode = Parking_022_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Parking_022_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Parking_022_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Parking_022_Mode((uint8)MODE_NORMAL);
    }
}
int Parking_022_Evaluate(void)
{
    int request = Parking_022_Decide();
    if (request < 0) {
        (void)Parking_022_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

#include "Parking_010.h"
#include "Rte_Parking_010.h"
void Parking_010_10ms(void)
{
    int mode = Parking_010_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Parking_010_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Parking_010_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Parking_010_Mode((uint8)MODE_NORMAL);
    }
}
int Parking_010_Evaluate(void)
{
    int request = Parking_010_Decide();
    if (request < 0) {
        (void)Parking_010_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

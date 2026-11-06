#include "Seat_006.h"
#include "Rte_Seat_006.h"
void Seat_006_10ms(void)
{
    int mode = Seat_006_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Seat_006_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Seat_006_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Seat_006_Mode((uint8)MODE_NORMAL);
    }
}
int Seat_006_Evaluate(void)
{
    int request = Seat_006_Decide();
    if (request < 0) {
        (void)Seat_006_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

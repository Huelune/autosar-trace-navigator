#include "Seat_018.h"
#include "Rte_Seat_018.h"
void Seat_018_10ms(void)
{
    int mode = Seat_018_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Seat_018_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Seat_018_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Seat_018_Mode((uint8)MODE_NORMAL);
    }
}
int Seat_018_Evaluate(void)
{
    int request = Seat_018_Decide();
    if (request < 0) {
        (void)Seat_018_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

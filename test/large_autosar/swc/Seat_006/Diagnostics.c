#include "Seat_006.h"

int Seat_006_Diagnostic(int value)
{
    switch (value) {
    case -1: return 1;
    case 0: return 0;
    default:
        if (value > 0) return 2;
        else return 3;
    }
}

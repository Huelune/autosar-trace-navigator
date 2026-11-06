#include "Cruise_021.h"

int Cruise_021_Diagnostic(int value)
{
    switch (value) {
    case -1: return 1;
    case 0: return 0;
    default:
        if (value > 0) return 2;
        else return 3;
    }
}

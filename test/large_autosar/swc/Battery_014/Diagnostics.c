#include "Battery_014.h"

int Battery_014_Diagnostic(int value)
{
    int count = 0;
    int i;
    for (i = 0; i < 3; ++i) {
        if (value < i) ++count;
        else if (value == i) count += 2;
        else count += 3;
    }
    return count;
}

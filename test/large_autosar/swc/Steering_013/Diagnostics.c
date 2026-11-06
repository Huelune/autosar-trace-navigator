#include "Steering_013.h"

int Steering_013_Diagnostic(int value)
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

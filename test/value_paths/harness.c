#include "value_paths.h"
#include <stdio.h>

int main(void)
{
    const unsigned cases[][4] = {
        {25u, 1u, 2u, 1u},
        {24u, 1u, 2u, 0u},
        {25u, 0u, 2u, 0u},
        {25u, 1u, 0u, 0u},
        {25u, 1u, 3u, 0u},
        {26u, 1u, 2u, 1u}
    };
    unsigned index;
    for (index = 0u; index < sizeof(cases) / sizeof(cases[0]); ++index) {
        ValuePath_RawInput = cases[index][0];
        ValuePath_EnableInput = cases[index][1];
        ValuePath_ModeInput = cases[index][2];
        (void)Rte_Write_ValuePath_Pedal(0u);
        ValuePath_PreparePermit();
        ValuePath_Produce();
        if ((unsigned)ValuePath_Consume() != cases[index][3]) {
            return 1;
        }
    }
    puts("PASS guarded value paths: 6 scenarios");
    return 0;
}

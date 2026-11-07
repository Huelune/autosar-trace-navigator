#include "struct_paths.h"
#include <stdio.h>

int main(void)
{
    const struct {
        unsigned raw;
        unsigned enable;
        unsigned read_status;
        int member_expected;
        int rte_expected;
    } cases[] = {
        {25u, 1u, 0u, 1, 1},
        {24u, 1u, 0u, 0, 0},
        {25u, 0u, 0u, 0, 0},
        {26u, 1u, 0u, 1, 1},
        {0u, 1u, 0u, 0, 0},
        {25u, 1u, 1u, 1, -1}
    };
    unsigned i;
    for (i = 0u; i < (unsigned)(sizeof(cases) / sizeof(cases[0])); ++i) {
        Struct_RawInput = cases[i].raw;
        Struct_EnableInput = cases[i].enable;
        Struct_ReadStatus = cases[i].read_status;
        Struct_Produce();
        if (Struct_Consume() != cases[i].rte_expected ||
            Struct_RunPointer() != cases[i].rte_expected ||
            Struct_ConsumeMember() != cases[i].rte_expected ||
            Struct_ConsumeGlobal() != cases[i].member_expected) {
            printf("FAIL struct paths scenario %u\n", i);
            return 1;
        }
    }
    puts("PASS struct paths: 6 scenarios");
    return 0;
}

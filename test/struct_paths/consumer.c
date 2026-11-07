#include "Rte_StructPaths.h"

int Struct_Consume(void)
{
    StructState b = {.a = 0u, .enabled = 0u};
    unsigned a;
    if (Rte_Read_Struct_State(&b) != 0) {
        return -1;
    }
    a = b.a;
    if (a >= (6u * 10u)) {
        return 1;
    }
    return 0;
}

int Struct_ConsumePointer(const StructState *p)
{
    if (p->a >= (6u * 10u)) {
        return 1;
    }
    return 0;
}

int Struct_RunPointer(void)
{
    StructState local = {.a = 0u, .enabled = 0u};
    if (Rte_Read_Struct_State(&local) != 0) {
        return -1;
    }
    return Struct_ConsumePointer(&local);
}

int Struct_ConsumeMember(void)
{
    StructState b = {.a = 0u, .enabled = 0u};
    if (Rte_Read_Struct_A(&b.a) != 0) {
        return -1;
    }
    if (b.a >= (6u * 10u)) {
        return 1;
    }
    return 0;
}

int Struct_ConsumeGlobal(void)
{
    if (Struct_ExternalState.a >= (6u * 10u)) {
        return 1;
    }
    return 0;
}

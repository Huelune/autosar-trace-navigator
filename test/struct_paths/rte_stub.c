#include "Rte_StructPaths.h"

unsigned Struct_ReadStatus;
static StructState struct_buffer;
static unsigned member_buffer;

int Rte_Read_Struct_State(StructState *value)
{
    if (Struct_ReadStatus != 0u) {
        return 1;
    }
    *value = struct_buffer;
    return 0;
}

int Rte_Write_Struct_State(const StructState *value)
{
    struct_buffer = *value;
    return 0;
}

int Rte_Read_Struct_A(unsigned *value)
{
    if (Struct_ReadStatus != 0u) {
        return 1;
    }
    *value = member_buffer;
    return 0;
}

int Rte_Write_Struct_A(unsigned value)
{
    member_buffer = value;
    return 0;
}

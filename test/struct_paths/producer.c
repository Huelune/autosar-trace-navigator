#include "Rte_StructPaths.h"

unsigned Struct_RawInput;
unsigned Struct_EnableInput;
StructState Struct_ExternalState;

static void Struct_SetMember(StructState *out)
{
    if (Struct_EnableInput == 1u) {
        out->a = Struct_RawInput * 2u + 10u;
        out->enabled = 1u;
    } else {
        out->a = 0u;
        out->enabled = 0u;
    }
}

static StructState Struct_MakeState(void)
{
    StructState made = {.a = 0u, .enabled = 0u};
    Struct_SetMember(&made);
    return made;
}

static void Struct_Fill(StructState *out)
{
    *out = Struct_MakeState();
}

static StructState Struct_BuildState(void)
{
    StructState state = {.a = 0u, .enabled = 0u};
    Struct_Fill(&state);
    return state;
}

void Struct_Produce(void)
{
    StructState built = Struct_BuildState();
    Struct_ExternalState = built;
    (void)Rte_Write_Struct_State(&built);
    (void)Rte_Write_Struct_A(built.a);
}

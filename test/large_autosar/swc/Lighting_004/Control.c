#include "Lighting_004.h"
#include "Rte_Lighting_004.h"
void Lighting_004_10ms(void)
{
    int mode = Lighting_004_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Lighting_004_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Lighting_004_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Lighting_004_Mode((uint8)MODE_NORMAL);
    }
}
int Lighting_004_Evaluate(void)
{
    int request = Lighting_004_Decide();
    if (request < 0) {
        (void)Lighting_004_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

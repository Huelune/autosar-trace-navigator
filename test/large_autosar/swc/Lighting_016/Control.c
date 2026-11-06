#include "Lighting_016.h"
#include "Rte_Lighting_016.h"
void Lighting_016_10ms(void)
{
    int mode = Lighting_016_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Lighting_016_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Lighting_016_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Lighting_016_Mode((uint8)MODE_NORMAL);
    }
}
int Lighting_016_Evaluate(void)
{
    int request = Lighting_016_Decide();
    if (request < 0) {
        (void)Lighting_016_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

#include "Thermal_015.h"
#include "Rte_Thermal_015.h"
void Thermal_015_10ms(void)
{
    int mode = Thermal_015_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Thermal_015_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Thermal_015_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Thermal_015_Mode((uint8)MODE_NORMAL);
    }
}
int Thermal_015_Evaluate(void)
{
    int request = Thermal_015_Decide();
    if (request < 0) {
        (void)Thermal_015_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

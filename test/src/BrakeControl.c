#include "BrakeControl.h"
#include "Rte_BrakeControl.h"

void BrakeControl_10ms(void)
{
    BrakeMode mode = EvaluateBrakeMode();

    if (mode == BRAKE_FAULT) {
        (void)Rte_Write_Brake_Mode((uint8)BRAKE_FAULT);
    } else if (mode == BRAKE_ASSIST) {
        /* TARGET_BRANCH: follow six call edges to the RTE speed input. */
        (void)Rte_Write_Brake_Mode((uint8)BRAKE_ASSIST);
    } else {
        (void)Rte_Write_Brake_Mode((uint8)BRAKE_NORMAL);
    }
}

BrakeMode EvaluateBrakeMode(void)
{
    int requested = IsAssistRequested();

    if (requested < 0) {
        return BRAKE_FAULT;
    } else if (requested == 1) {
        return BRAKE_ASSIST;
    } else {
        return BRAKE_NORMAL;
    }
}

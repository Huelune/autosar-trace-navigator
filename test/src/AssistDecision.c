#include "BrakeControl.h"
#include "Rte_BrakeControl.h"

int IsAssistRequested(void)
{
    int eligible = IsSpeedEligible();
    uint8 pedal = 0u;

    if (eligible < 0) {
        return -1;
    } else if (Rte_Read_Pedal_Percent(&pedal) != E_OK) {
        return -1;
    } else if (pedal > 100u) {
        return -1;
    } else {
        if ((eligible == 1) && (pedal >= 60u)) {
            return 1;
        } else {
            return 0;
        }
    }
}

int IsSpeedEligible(void)
{
    int speed = GetValidatedSpeed();

    if (speed < 0) {
        return -1;
    } else if (speed >= 30) {
        return 1;
    } else {
        return 0;
    }
}

#include "BrakeControl.h"
#include "Rte_BrakeControl.h"

/* Demonstrates a macro whose meaning needs header/preprocessor context. */
#define RAW_TO_KPH(raw) ((raw) / 10)

int GetValidatedSpeed(void)
{
    int speed = DecodeSpeed();

    if (speed < 0) {
        return -1;
    } else if (speed > 250) {
        return -1;
    } else {
        return speed;
    }
}

int DecodeSpeed(void)
{
    int raw = ReadRawSpeed();

    if (raw < 0) {
        return -1;
    } else if (raw == 65535) {
        return -1;
    } else {
        return RAW_TO_KPH(raw);
    }
}

int ReadRawSpeed(void)
{
    uint16 raw = 0u;

    if (Rte_Read_Speed_Raw(&raw) != E_OK) {
        return -1;
    } else {
        return (int)raw;
    }
}

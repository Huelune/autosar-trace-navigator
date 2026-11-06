#include "Steering_001.h"
#include "Rte_Steering_001.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Steering_001_Validated(void)
{
    int value = Steering_001_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Steering_001_Decode(void)
{
    int raw = Steering_001_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Steering_001_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Steering_001_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

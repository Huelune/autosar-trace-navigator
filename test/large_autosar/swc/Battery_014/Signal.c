#include "Battery_014.h"
#include "Rte_Battery_014.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Battery_014_Validated(void)
{
    int value = Battery_014_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Battery_014_Decode(void)
{
    int raw = Battery_014_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Battery_014_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Battery_014_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

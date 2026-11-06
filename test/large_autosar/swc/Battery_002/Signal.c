#include "Battery_002.h"
#include "Rte_Battery_002.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Battery_002_Validated(void)
{
    int value = Battery_002_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Battery_002_Decode(void)
{
    int raw = Battery_002_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Battery_002_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Battery_002_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

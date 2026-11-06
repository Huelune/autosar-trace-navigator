#include "Lighting_016.h"
#include "Rte_Lighting_016.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Lighting_016_Validated(void)
{
    int value = Lighting_016_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Lighting_016_Decode(void)
{
    int raw = Lighting_016_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Lighting_016_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Lighting_016_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

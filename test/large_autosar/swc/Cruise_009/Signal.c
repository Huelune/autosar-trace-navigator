#include "Cruise_009.h"
#include "Rte_Cruise_009.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Cruise_009_Validated(void)
{
    int value = Cruise_009_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Cruise_009_Decode(void)
{
    int raw = Cruise_009_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Cruise_009_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Cruise_009_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

#include "Thermal_015.h"
#include "Rte_Thermal_015.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Thermal_015_Validated(void)
{
    int value = Thermal_015_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Thermal_015_Decode(void)
{
    int raw = Thermal_015_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Thermal_015_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Thermal_015_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

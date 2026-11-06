#include "Charging_023.h"
#include "Rte_Charging_023.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Charging_023_Validated(void)
{
    int value = Charging_023_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Charging_023_Decode(void)
{
    int raw = Charging_023_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Charging_023_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Charging_023_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

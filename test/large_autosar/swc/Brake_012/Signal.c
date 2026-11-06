#include "Brake_012.h"
#include "Rte_Brake_012.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Brake_012_Validated(void)
{
    int value = Brake_012_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Brake_012_Decode(void)
{
    int raw = Brake_012_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Brake_012_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Brake_012_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

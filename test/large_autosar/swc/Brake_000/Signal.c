#include "Brake_000.h"
#include "Rte_Brake_000.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Brake_000_Validated(void)
{
    int value = Brake_000_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Brake_000_Decode(void)
{
    int raw = Brake_000_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Brake_000_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Brake_000_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

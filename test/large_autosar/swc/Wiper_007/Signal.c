#include "Wiper_007.h"
#include "Rte_Wiper_007.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Wiper_007_Validated(void)
{
    int value = Wiper_007_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Wiper_007_Decode(void)
{
    int raw = Wiper_007_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Wiper_007_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Wiper_007_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

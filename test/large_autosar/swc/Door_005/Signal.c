#include "Door_005.h"
#include "Rte_Door_005.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Door_005_Validated(void)
{
    int value = Door_005_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Door_005_Decode(void)
{
    int raw = Door_005_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Door_005_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Door_005_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

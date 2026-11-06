#include "Parking_022.h"
#include "Rte_Parking_022.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Parking_022_Validated(void)
{
    int value = Parking_022_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Parking_022_Decode(void)
{
    int raw = Parking_022_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Parking_022_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Parking_022_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

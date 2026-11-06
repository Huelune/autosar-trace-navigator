#include "Parking_010.h"
#include "Rte_Parking_010.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Parking_010_Validated(void)
{
    int value = Parking_010_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Parking_010_Decode(void)
{
    int raw = Parking_010_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Parking_010_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Parking_010_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

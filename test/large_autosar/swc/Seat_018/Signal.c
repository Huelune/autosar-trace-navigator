#include "Seat_018.h"
#include "Rte_Seat_018.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Seat_018_Validated(void)
{
    int value = Seat_018_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Seat_018_Decode(void)
{
    int raw = Seat_018_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Seat_018_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Seat_018_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

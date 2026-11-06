#include "Cluster_020.h"
#include "Rte_Cluster_020.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{
    return SENSOR_TO_UNIT(raw);
}
int Cluster_020_Validated(void)
{
    int value = Cluster_020_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}
int Cluster_020_Decode(void)
{
    int raw = Cluster_020_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}
int Cluster_020_Read(void)
{
    uint16 raw = 0u;
    if (Rte_Read_Cluster_020_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}

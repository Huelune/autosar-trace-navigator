#ifndef RTE_SENSOR_ACQUISITION_H
#define RTE_SENSOR_ACQUISITION_H

/* Synthetic sender side of the same speed and pedal data elements. */
#include "Std_Types.h"

Std_ReturnType Rte_Write_Speed_Raw(uint16 value);
Std_ReturnType Rte_Write_Pedal_Percent(uint8 value);

#endif

#ifndef RTE_BATTERY_014_H
#define RTE_BATTERY_014_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Battery_014.h"
Std_ReturnType Rte_Read_Battery_014_Signal_Raw(uint16 *value);
Std_ReturnType Rte_Read_Battery_014_Demand_Percent(uint8 *value);
Std_ReturnType Rte_Write_Battery_014_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Battery_014_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Battery_014_Mode(uint8 value);
#endif

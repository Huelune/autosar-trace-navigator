#ifndef RTE_THERMAL_015_H
#define RTE_THERMAL_015_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Thermal_015.h"
Std_ReturnType Rte_Read_Thermal_015_Signal_Raw(uint16 *value);
Std_ReturnType Rte_Read_Thermal_015_Demand_Percent(uint8 *value);
Std_ReturnType Rte_Write_Thermal_015_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Thermal_015_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Thermal_015_Mode(uint8 value);
#endif

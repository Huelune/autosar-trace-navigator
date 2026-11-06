#ifndef RTE_THERMAL_003_H
#define RTE_THERMAL_003_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Thermal_003.h"
Std_ReturnType Rte_Read_Thermal_003_Signal_Raw(uint16 *value);
Std_ReturnType Rte_Read_Thermal_003_Demand_Percent(uint8 *value);
Std_ReturnType Rte_Write_Thermal_003_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Thermal_003_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Thermal_003_Mode(uint8 value);
#endif

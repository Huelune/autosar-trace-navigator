#ifndef RTE_CHARGING_011_H
#define RTE_CHARGING_011_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Charging_011.h"
Std_ReturnType Rte_Read_Charging_011_Signal_Raw(uint16 *value);
Std_ReturnType Rte_Read_Charging_011_Demand_Percent(uint8 *value);
Std_ReturnType Rte_Write_Charging_011_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Charging_011_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Charging_011_Mode(uint8 value);
#endif

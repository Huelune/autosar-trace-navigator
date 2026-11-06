#ifndef RTE_CRUISE_021_H
#define RTE_CRUISE_021_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Cruise_021.h"
Std_ReturnType Rte_Read_Cruise_021_Signal_Raw(uint16 *value);
Std_ReturnType Rte_Impl_Read_Cruise_021_Demand_Percent(uint8 *value);
#define Rte_Read_Cruise_021_Demand_Percent Rte_Impl_Read_Cruise_021_Demand_Percent
Std_ReturnType Rte_Write_Cruise_021_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Cruise_021_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Cruise_021_Mode(uint8 value);
#endif

#ifndef RTE_STEERING_013_H
#define RTE_STEERING_013_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Steering_013.h"
Std_ReturnType Rte_Read_Steering_013_Signal_Raw(uint16 *value);
Std_ReturnType Rte_Impl_Read_Steering_013_Demand_Percent(uint8 *value);
#define Rte_Read_Steering_013_Demand_Percent Rte_Impl_Read_Steering_013_Demand_Percent
Std_ReturnType Rte_Write_Steering_013_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Steering_013_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Steering_013_Mode(uint8 value);
#endif

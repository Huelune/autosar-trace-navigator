#ifndef RTE_BRAKE_012_H
#define RTE_BRAKE_012_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Brake_012.h"
Std_ReturnType Rte_Impl_Read_Brake_012_Signal_Raw(uint16 *value);
#define Rte_Read_Brake_012_Signal_Raw(p) Rte_Impl_Read_Brake_012_Signal_Raw(p)
Std_ReturnType Rte_Read_Brake_012_Demand_Percent(uint8 *value);
Std_ReturnType Rte_Write_Brake_012_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Brake_012_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Brake_012_Mode(uint8 value);
#endif

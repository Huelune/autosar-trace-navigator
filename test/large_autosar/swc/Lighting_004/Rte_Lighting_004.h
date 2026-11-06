#ifndef RTE_LIGHTING_004_H
#define RTE_LIGHTING_004_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Lighting_004.h"
Std_ReturnType Rte_Impl_Read_Lighting_004_Signal_Raw(uint16 *value);
#define Rte_Read_Lighting_004_Signal_Raw(p) Rte_Impl_Read_Lighting_004_Signal_Raw(p)
Std_ReturnType Rte_Read_Lighting_004_Demand_Percent(uint8 *value);
Std_ReturnType Rte_Write_Lighting_004_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Lighting_004_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Lighting_004_Mode(uint8 value);
#endif

#ifndef RTE_LIGHTING_016_H
#define RTE_LIGHTING_016_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Lighting_016.h"
Std_ReturnType Rte_Impl_Read_Lighting_016_Signal_Raw(uint16 *value);
#define Rte_Read_Lighting_016_Signal_Raw(p) Rte_Impl_Read_Lighting_016_Signal_Raw(p)
Std_ReturnType Rte_Read_Lighting_016_Demand_Percent(uint8 *value);
Std_ReturnType Rte_Write_Lighting_016_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Lighting_016_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Lighting_016_Mode(uint8 value);
#endif

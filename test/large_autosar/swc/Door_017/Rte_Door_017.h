#ifndef RTE_DOOR_017_H
#define RTE_DOOR_017_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Door_017.h"
Std_ReturnType Rte_Read_Door_017_Signal_Raw(uint16 *value);
Std_ReturnType Rte_Impl_Read_Door_017_Demand_Percent(uint8 *value);
#define Rte_Read_Door_017_Demand_Percent Rte_Impl_Read_Door_017_Demand_Percent
Std_ReturnType Rte_Write_Door_017_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Door_017_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Door_017_Mode(uint8 value);
#endif

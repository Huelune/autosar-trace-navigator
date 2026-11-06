#ifndef RTE_BRAKE_CONTROL_H
#define RTE_BRAKE_CONTROL_H

/* Synthetic generated-style header; no vendor code or real RTE generator. */
#include "Std_Types.h"

Std_ReturnType Rte_Read_Speed_Raw(uint16 *value);
Std_ReturnType Rte_Read_Pedal_Percent(uint8 *value);
Std_ReturnType Rte_Write_Brake_Mode(uint8 value);

#endif

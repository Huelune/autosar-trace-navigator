#ifndef RTE_CLUSTER_008_H
#define RTE_CLUSTER_008_H
/* Synthetic generated-style declarations, not vendor code. */
#include "Cluster_008.h"
Std_ReturnType Rte_Impl_Read_Cluster_008_Signal_Raw(uint16 *value);
#define Rte_Read_Cluster_008_Signal_Raw(p) Rte_Impl_Read_Cluster_008_Signal_Raw(p)
Std_ReturnType Rte_Read_Cluster_008_Demand_Percent(uint8 *value);
Std_ReturnType Rte_Write_Cluster_008_Signal_Raw(uint16 value);
Std_ReturnType Rte_Write_Cluster_008_Demand_Percent(uint8 value);
Std_ReturnType Rte_Write_Cluster_008_Mode(uint8 value);
#endif

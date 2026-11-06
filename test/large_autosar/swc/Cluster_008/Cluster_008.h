#ifndef CLUSTER_008_H
#define CLUSTER_008_H
#include "../../shared/Std_Types.h"
void Cluster_008_10ms(void);
void Cluster_008_Producer(void);
uint16 Cluster_008_AcquireRaw(void);
uint8 Cluster_008_AcquireDemand(void);
int Cluster_008_Evaluate(void);
int Cluster_008_Decide(void);
int Cluster_008_Eligible(void);
int Cluster_008_Validated(void);
int Cluster_008_Decode(void);
int Cluster_008_Read(void);
int Cluster_008_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

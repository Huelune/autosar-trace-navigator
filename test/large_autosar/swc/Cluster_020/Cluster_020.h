#ifndef CLUSTER_020_H
#define CLUSTER_020_H
#include "../../shared/Std_Types.h"
void Cluster_020_10ms(void);
void Cluster_020_Producer(void);
uint16 Cluster_020_AcquireRaw(void);
uint8 Cluster_020_AcquireDemand(void);
int Cluster_020_Evaluate(void);
int Cluster_020_Decide(void);
int Cluster_020_Eligible(void);
int Cluster_020_Validated(void);
int Cluster_020_Decode(void);
int Cluster_020_Read(void);
int Cluster_020_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif

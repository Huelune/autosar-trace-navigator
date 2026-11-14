#ifndef ORIGINS_H
#define ORIGINS_H
extern unsigned Preview_Raw;
extern unsigned Preview_Enable;
extern unsigned Preview_Quality;
unsigned Origin_First(void);
unsigned External_Unknown(void);
int Rte_Read_Preview_Pedal(unsigned *value);
int Rte_Write_Preview_Pedal(unsigned value);
#endif

#ifndef VALUE_PATHS_H
#define VALUE_PATHS_H

/* Fictional CT-visible inputs: accessibility still depends on the test build. */
extern unsigned ValuePath_RawInput;
extern unsigned ValuePath_EnableInput;
extern unsigned ValuePath_ModeInput;

int Rte_Read_ValuePath_Pedal(unsigned *value);
int Rte_Write_ValuePath_Pedal(unsigned value);
void ValuePath_PreparePermit(void);
void ValuePath_Produce(void);
int ValuePath_Consume(void);

#endif

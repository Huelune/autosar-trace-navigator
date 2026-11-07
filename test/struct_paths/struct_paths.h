/* Fictional AUTOSAR-style structure payload; no customer source. */
#ifndef STRUCT_PATHS_H
#define STRUCT_PATHS_H

typedef struct {
    unsigned a;
    unsigned enabled;
} StructState;

extern unsigned Struct_RawInput;
extern unsigned Struct_EnableInput;
extern unsigned Struct_ReadStatus;
extern StructState Struct_ExternalState;

void Struct_Produce(void);
int Struct_Consume(void);
int Struct_ConsumePointer(const StructState *p);
int Struct_RunPointer(void);
int Struct_ConsumeMember(void);
int Struct_ConsumeGlobal(void);

#endif

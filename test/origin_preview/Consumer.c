#include "Origins.h"
unsigned Origin_Last(void)
{
    unsigned pedal = 0u;
    (void)Rte_Read_Preview_Pedal(&pedal);
    return pedal;
}
unsigned Origin_Middle(void) { return Origin_Last(); }
unsigned Origin_First(void) { return Origin_Middle(); }
int Origin_Goal(void)
{
    unsigned pedal = Origin_First();
    if (pedal >= 60u) { return 1; }
    return 0;
}
unsigned Origin_Cycle(void) { return Origin_Cycle(); }
unsigned Origin_Missing(void) { unsigned x = External_Unknown(); return x; }
unsigned Origin_Array(unsigned *table) { return table[0]; }

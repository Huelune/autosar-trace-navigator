/* Fictional AUTOSAR-style data flow; deliberately no literal target input. */
#include "value_paths.h"

#define VALUE_PATH_TARGET (6u * 10u)

unsigned ValuePath_RawInput;
unsigned ValuePath_EnableInput;
unsigned ValuePath_ModeInput;
static unsigned value_path_permit;
static unsigned value_path_rte_memory;

int Rte_Read_ValuePath_Pedal(unsigned *value)
{
    *value = value_path_rte_memory;
    return 0;
}

int Rte_Write_ValuePath_Pedal(unsigned value)
{
    value_path_rte_memory = value;
    return 0;
}

void ValuePath_PreparePermit(void)
{
    if (ValuePath_EnableInput == 1u) {
        value_path_permit = 1u;
    } else {
        value_path_permit = 0u;
    }
}

void ValuePath_Produce(void)
{
    unsigned next = 0u;
    if (ValuePath_ModeInput == 0u) {
        next = 0u;
    } else if (ValuePath_ModeInput == 2u) {
        if (value_path_permit != 0u) {
            next = ValuePath_RawInput * 2u + 10u;
        }
    } else {
        next = 0u;
    }
    (void)Rte_Write_ValuePath_Pedal(next);
}

int ValuePath_Consume(void)
{
    unsigned pedal = 0u;
    (void)Rte_Read_ValuePath_Pedal(&pedal);
    if (pedal >= VALUE_PATH_TARGET) {
        return 1;
    }
    return 0;
}

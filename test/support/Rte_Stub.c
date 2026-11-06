#include "Rte_BrakeControl.h"
#include "Rte_SensorAcquisition.h"
#include "TestPlatform.h"

/* In-memory test double: not an AUTOSAR RTE implementation. */
static uint16 hardware_speed;
static uint8 hardware_pedal;
static uint16 speed_buffer;
static uint8 pedal_buffer;
static Std_ReturnType speed_read_status;
static Std_ReturnType pedal_read_status;
static uint8 last_mode;
static unsigned int mode_writes;

void TestPlatform_Reset(uint16 speed, uint8 pedal,
                        Std_ReturnType speed_status,
                        Std_ReturnType pedal_status)
{
    hardware_speed = speed;
    hardware_pedal = pedal;
    speed_buffer = 0u;
    pedal_buffer = 0u;
    speed_read_status = speed_status;
    pedal_read_status = pedal_status;
    last_mode = 0u;
    mode_writes = 0u;
}

uint16 IoHwAb_ReadSpeedRaw(void) { return hardware_speed; }
uint8 IoHwAb_ReadPedalPercent(void) { return hardware_pedal; }

Std_ReturnType Rte_Write_Speed_Raw(uint16 value)
{
    speed_buffer = value;
    return E_OK;
}

Std_ReturnType Rte_Write_Pedal_Percent(uint8 value)
{
    pedal_buffer = value;
    return E_OK;
}

Std_ReturnType Rte_Read_Speed_Raw(uint16 *value)
{
    if (speed_read_status != E_OK) {
        return speed_read_status;
    } else {
        *value = speed_buffer;
        return E_OK;
    }
}

Std_ReturnType Rte_Read_Pedal_Percent(uint8 *value)
{
    if (pedal_read_status != E_OK) {
        return pedal_read_status;
    } else {
        *value = pedal_buffer;
        return E_OK;
    }
}

Std_ReturnType Rte_Write_Brake_Mode(uint8 value)
{
    last_mode = value;
    ++mode_writes;
    return E_OK;
}

uint8 TestPlatform_LastMode(void) { return last_mode; }
unsigned int TestPlatform_ModeWrites(void) { return mode_writes; }

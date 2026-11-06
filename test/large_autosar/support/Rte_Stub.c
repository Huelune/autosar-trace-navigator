#include "../shared/Std_Types.h"
#define COMPONENT_COUNT 24u
static uint16 hardware_raw[COMPONENT_COUNT], raw_buffer[COMPONENT_COUNT];
static uint8 hardware_demand[COMPONENT_COUNT], demand_buffer[COMPONENT_COUNT], last_mode[COMPONENT_COUNT];
static Std_ReturnType raw_status[COMPONENT_COUNT], demand_status[COMPONENT_COUNT];
static unsigned int mode_writes[COMPONENT_COUNT];
void Platform_Setup(unsigned int index, uint16 raw, uint8 demand,
                    Std_ReturnType raw_ok, Std_ReturnType demand_ok)
{
    hardware_raw[index] = raw;
    hardware_demand[index] = demand;
    raw_status[index] = raw_ok;
    demand_status[index] = demand_ok;
    raw_buffer[index] = 0u;
    demand_buffer[index] = 0u;
    last_mode[index] = 0u;
    mode_writes[index] = 0u;
}
uint16 Platform_ReadRaw(unsigned int index) { return hardware_raw[index]; }
uint8 Platform_ReadDemand(unsigned int index) { return hardware_demand[index]; }
uint8 Platform_Mode(unsigned int index) { return last_mode[index]; }
unsigned int Platform_Writes(unsigned int index) { return mode_writes[index]; }
Std_ReturnType Rte_Impl_Read_Brake_000_Signal_Raw(uint16 *value)
{
    if (raw_status[0] != E_OK) return raw_status[0];
    *value = raw_buffer[0];
    return E_OK;
}
Std_ReturnType Rte_Read_Brake_000_Demand_Percent(uint8 *value)
{
    if (demand_status[0] != E_OK) return demand_status[0];
    *value = demand_buffer[0];
    return E_OK;
}
Std_ReturnType Rte_Write_Brake_000_Signal_Raw(uint16 value)
{

    raw_buffer[0] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Brake_000_Demand_Percent(uint8 value)
{

    demand_buffer[0] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Brake_000_Mode(uint8 value)
{

    last_mode[0] = value; ++mode_writes[0];
    return E_OK;
}
Std_ReturnType Rte_Read_Steering_001_Signal_Raw(uint16 *value)
{
    if (raw_status[1] != E_OK) return raw_status[1];
    *value = raw_buffer[1];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Steering_001_Demand_Percent(uint8 *value)
{
    if (demand_status[1] != E_OK) return demand_status[1];
    *value = demand_buffer[1];
    return E_OK;
}
Std_ReturnType Rte_Write_Steering_001_Signal_Raw(uint16 value)
{

    raw_buffer[1] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Steering_001_Demand_Percent(uint8 value)
{

    demand_buffer[1] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Steering_001_Mode(uint8 value)
{

    last_mode[1] = value; ++mode_writes[1];
    return E_OK;
}
Std_ReturnType Rte_Read_Battery_002_Signal_Raw(uint16 *value)
{
    if (raw_status[2] != E_OK) return raw_status[2];
    *value = raw_buffer[2];
    return E_OK;
}
Std_ReturnType Rte_Read_Battery_002_Demand_Percent(uint8 *value)
{
    if (demand_status[2] != E_OK) return demand_status[2];
    *value = demand_buffer[2];
    return E_OK;
}
Std_ReturnType Rte_Write_Battery_002_Signal_Raw(uint16 value)
{

    raw_buffer[2] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Battery_002_Demand_Percent(uint8 value)
{

    demand_buffer[2] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Battery_002_Mode(uint8 value)
{

    last_mode[2] = value; ++mode_writes[2];
    return E_OK;
}
Std_ReturnType Rte_Read_Thermal_003_Signal_Raw(uint16 *value)
{
    if (raw_status[3] != E_OK) return raw_status[3];
    *value = raw_buffer[3];
    return E_OK;
}
Std_ReturnType Rte_Read_Thermal_003_Demand_Percent(uint8 *value)
{
    if (demand_status[3] != E_OK) return demand_status[3];
    *value = demand_buffer[3];
    return E_OK;
}
Std_ReturnType Rte_Write_Thermal_003_Signal_Raw(uint16 value)
{

    raw_buffer[3] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Thermal_003_Demand_Percent(uint8 value)
{

    demand_buffer[3] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Thermal_003_Mode(uint8 value)
{

    last_mode[3] = value; ++mode_writes[3];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Lighting_004_Signal_Raw(uint16 *value)
{
    if (raw_status[4] != E_OK) return raw_status[4];
    *value = raw_buffer[4];
    return E_OK;
}
Std_ReturnType Rte_Read_Lighting_004_Demand_Percent(uint8 *value)
{
    if (demand_status[4] != E_OK) return demand_status[4];
    *value = demand_buffer[4];
    return E_OK;
}
Std_ReturnType Rte_Write_Lighting_004_Signal_Raw(uint16 value)
{

    raw_buffer[4] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Lighting_004_Demand_Percent(uint8 value)
{

    demand_buffer[4] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Lighting_004_Mode(uint8 value)
{

    last_mode[4] = value; ++mode_writes[4];
    return E_OK;
}
Std_ReturnType Rte_Read_Door_005_Signal_Raw(uint16 *value)
{
    if (raw_status[5] != E_OK) return raw_status[5];
    *value = raw_buffer[5];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Door_005_Demand_Percent(uint8 *value)
{
    if (demand_status[5] != E_OK) return demand_status[5];
    *value = demand_buffer[5];
    return E_OK;
}
Std_ReturnType Rte_Write_Door_005_Signal_Raw(uint16 value)
{

    raw_buffer[5] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Door_005_Demand_Percent(uint8 value)
{

    demand_buffer[5] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Door_005_Mode(uint8 value)
{

    last_mode[5] = value; ++mode_writes[5];
    return E_OK;
}
Std_ReturnType Rte_Read_Seat_006_Signal_Raw(uint16 *value)
{
    if (raw_status[6] != E_OK) return raw_status[6];
    *value = raw_buffer[6];
    return E_OK;
}
Std_ReturnType Rte_Read_Seat_006_Demand_Percent(uint8 *value)
{
    if (demand_status[6] != E_OK) return demand_status[6];
    *value = demand_buffer[6];
    return E_OK;
}
Std_ReturnType Rte_Write_Seat_006_Signal_Raw(uint16 value)
{

    raw_buffer[6] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Seat_006_Demand_Percent(uint8 value)
{

    demand_buffer[6] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Seat_006_Mode(uint8 value)
{

    last_mode[6] = value; ++mode_writes[6];
    return E_OK;
}
Std_ReturnType Rte_Read_Wiper_007_Signal_Raw(uint16 *value)
{
    if (raw_status[7] != E_OK) return raw_status[7];
    *value = raw_buffer[7];
    return E_OK;
}
Std_ReturnType Rte_Read_Wiper_007_Demand_Percent(uint8 *value)
{
    if (demand_status[7] != E_OK) return demand_status[7];
    *value = demand_buffer[7];
    return E_OK;
}
Std_ReturnType Rte_Write_Wiper_007_Signal_Raw(uint16 value)
{

    raw_buffer[7] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Wiper_007_Demand_Percent(uint8 value)
{

    demand_buffer[7] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Wiper_007_Mode(uint8 value)
{

    last_mode[7] = value; ++mode_writes[7];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Cluster_008_Signal_Raw(uint16 *value)
{
    if (raw_status[8] != E_OK) return raw_status[8];
    *value = raw_buffer[8];
    return E_OK;
}
Std_ReturnType Rte_Read_Cluster_008_Demand_Percent(uint8 *value)
{
    if (demand_status[8] != E_OK) return demand_status[8];
    *value = demand_buffer[8];
    return E_OK;
}
Std_ReturnType Rte_Write_Cluster_008_Signal_Raw(uint16 value)
{

    raw_buffer[8] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Cluster_008_Demand_Percent(uint8 value)
{

    demand_buffer[8] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Cluster_008_Mode(uint8 value)
{

    last_mode[8] = value; ++mode_writes[8];
    return E_OK;
}
Std_ReturnType Rte_Read_Cruise_009_Signal_Raw(uint16 *value)
{
    if (raw_status[9] != E_OK) return raw_status[9];
    *value = raw_buffer[9];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Cruise_009_Demand_Percent(uint8 *value)
{
    if (demand_status[9] != E_OK) return demand_status[9];
    *value = demand_buffer[9];
    return E_OK;
}
Std_ReturnType Rte_Write_Cruise_009_Signal_Raw(uint16 value)
{

    raw_buffer[9] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Cruise_009_Demand_Percent(uint8 value)
{

    demand_buffer[9] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Cruise_009_Mode(uint8 value)
{

    last_mode[9] = value; ++mode_writes[9];
    return E_OK;
}
Std_ReturnType Rte_Read_Parking_010_Signal_Raw(uint16 *value)
{
    if (raw_status[10] != E_OK) return raw_status[10];
    *value = raw_buffer[10];
    return E_OK;
}
Std_ReturnType Rte_Read_Parking_010_Demand_Percent(uint8 *value)
{
    if (demand_status[10] != E_OK) return demand_status[10];
    *value = demand_buffer[10];
    return E_OK;
}
Std_ReturnType Rte_Write_Parking_010_Signal_Raw(uint16 value)
{

    raw_buffer[10] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Parking_010_Demand_Percent(uint8 value)
{

    demand_buffer[10] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Parking_010_Mode(uint8 value)
{

    last_mode[10] = value; ++mode_writes[10];
    return E_OK;
}
Std_ReturnType Rte_Read_Charging_011_Signal_Raw(uint16 *value)
{
    if (raw_status[11] != E_OK) return raw_status[11];
    *value = raw_buffer[11];
    return E_OK;
}
Std_ReturnType Rte_Read_Charging_011_Demand_Percent(uint8 *value)
{
    if (demand_status[11] != E_OK) return demand_status[11];
    *value = demand_buffer[11];
    return E_OK;
}
Std_ReturnType Rte_Write_Charging_011_Signal_Raw(uint16 value)
{

    raw_buffer[11] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Charging_011_Demand_Percent(uint8 value)
{

    demand_buffer[11] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Charging_011_Mode(uint8 value)
{

    last_mode[11] = value; ++mode_writes[11];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Brake_012_Signal_Raw(uint16 *value)
{
    if (raw_status[12] != E_OK) return raw_status[12];
    *value = raw_buffer[12];
    return E_OK;
}
Std_ReturnType Rte_Read_Brake_012_Demand_Percent(uint8 *value)
{
    if (demand_status[12] != E_OK) return demand_status[12];
    *value = demand_buffer[12];
    return E_OK;
}
Std_ReturnType Rte_Write_Brake_012_Signal_Raw(uint16 value)
{

    raw_buffer[12] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Brake_012_Demand_Percent(uint8 value)
{

    demand_buffer[12] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Brake_012_Mode(uint8 value)
{

    last_mode[12] = value; ++mode_writes[12];
    return E_OK;
}
Std_ReturnType Rte_Read_Steering_013_Signal_Raw(uint16 *value)
{
    if (raw_status[13] != E_OK) return raw_status[13];
    *value = raw_buffer[13];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Steering_013_Demand_Percent(uint8 *value)
{
    if (demand_status[13] != E_OK) return demand_status[13];
    *value = demand_buffer[13];
    return E_OK;
}
Std_ReturnType Rte_Write_Steering_013_Signal_Raw(uint16 value)
{

    raw_buffer[13] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Steering_013_Demand_Percent(uint8 value)
{

    demand_buffer[13] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Steering_013_Mode(uint8 value)
{

    last_mode[13] = value; ++mode_writes[13];
    return E_OK;
}
Std_ReturnType Rte_Read_Battery_014_Signal_Raw(uint16 *value)
{
    if (raw_status[14] != E_OK) return raw_status[14];
    *value = raw_buffer[14];
    return E_OK;
}
Std_ReturnType Rte_Read_Battery_014_Demand_Percent(uint8 *value)
{
    if (demand_status[14] != E_OK) return demand_status[14];
    *value = demand_buffer[14];
    return E_OK;
}
Std_ReturnType Rte_Write_Battery_014_Signal_Raw(uint16 value)
{

    raw_buffer[14] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Battery_014_Demand_Percent(uint8 value)
{

    demand_buffer[14] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Battery_014_Mode(uint8 value)
{

    last_mode[14] = value; ++mode_writes[14];
    return E_OK;
}
Std_ReturnType Rte_Read_Thermal_015_Signal_Raw(uint16 *value)
{
    if (raw_status[15] != E_OK) return raw_status[15];
    *value = raw_buffer[15];
    return E_OK;
}
Std_ReturnType Rte_Read_Thermal_015_Demand_Percent(uint8 *value)
{
    if (demand_status[15] != E_OK) return demand_status[15];
    *value = demand_buffer[15];
    return E_OK;
}
Std_ReturnType Rte_Write_Thermal_015_Signal_Raw(uint16 value)
{

    raw_buffer[15] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Thermal_015_Demand_Percent(uint8 value)
{

    demand_buffer[15] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Thermal_015_Mode(uint8 value)
{

    last_mode[15] = value; ++mode_writes[15];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Lighting_016_Signal_Raw(uint16 *value)
{
    if (raw_status[16] != E_OK) return raw_status[16];
    *value = raw_buffer[16];
    return E_OK;
}
Std_ReturnType Rte_Read_Lighting_016_Demand_Percent(uint8 *value)
{
    if (demand_status[16] != E_OK) return demand_status[16];
    *value = demand_buffer[16];
    return E_OK;
}
Std_ReturnType Rte_Write_Lighting_016_Signal_Raw(uint16 value)
{

    raw_buffer[16] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Lighting_016_Demand_Percent(uint8 value)
{

    demand_buffer[16] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Lighting_016_Mode(uint8 value)
{

    last_mode[16] = value; ++mode_writes[16];
    return E_OK;
}
Std_ReturnType Rte_Read_Door_017_Signal_Raw(uint16 *value)
{
    if (raw_status[17] != E_OK) return raw_status[17];
    *value = raw_buffer[17];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Door_017_Demand_Percent(uint8 *value)
{
    if (demand_status[17] != E_OK) return demand_status[17];
    *value = demand_buffer[17];
    return E_OK;
}
Std_ReturnType Rte_Write_Door_017_Signal_Raw(uint16 value)
{

    raw_buffer[17] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Door_017_Demand_Percent(uint8 value)
{

    demand_buffer[17] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Door_017_Mode(uint8 value)
{

    last_mode[17] = value; ++mode_writes[17];
    return E_OK;
}
Std_ReturnType Rte_Read_Seat_018_Signal_Raw(uint16 *value)
{
    if (raw_status[18] != E_OK) return raw_status[18];
    *value = raw_buffer[18];
    return E_OK;
}
Std_ReturnType Rte_Read_Seat_018_Demand_Percent(uint8 *value)
{
    if (demand_status[18] != E_OK) return demand_status[18];
    *value = demand_buffer[18];
    return E_OK;
}
Std_ReturnType Rte_Write_Seat_018_Signal_Raw(uint16 value)
{

    raw_buffer[18] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Seat_018_Demand_Percent(uint8 value)
{

    demand_buffer[18] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Seat_018_Mode(uint8 value)
{

    last_mode[18] = value; ++mode_writes[18];
    return E_OK;
}
Std_ReturnType Rte_Read_Wiper_019_Signal_Raw(uint16 *value)
{
    if (raw_status[19] != E_OK) return raw_status[19];
    *value = raw_buffer[19];
    return E_OK;
}
Std_ReturnType Rte_Read_Wiper_019_Demand_Percent(uint8 *value)
{
    if (demand_status[19] != E_OK) return demand_status[19];
    *value = demand_buffer[19];
    return E_OK;
}
Std_ReturnType Rte_Write_Wiper_019_Signal_Raw(uint16 value)
{

    raw_buffer[19] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Wiper_019_Demand_Percent(uint8 value)
{

    demand_buffer[19] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Wiper_019_Mode(uint8 value)
{

    last_mode[19] = value; ++mode_writes[19];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Cluster_020_Signal_Raw(uint16 *value)
{
    if (raw_status[20] != E_OK) return raw_status[20];
    *value = raw_buffer[20];
    return E_OK;
}
Std_ReturnType Rte_Read_Cluster_020_Demand_Percent(uint8 *value)
{
    if (demand_status[20] != E_OK) return demand_status[20];
    *value = demand_buffer[20];
    return E_OK;
}
Std_ReturnType Rte_Write_Cluster_020_Signal_Raw(uint16 value)
{

    raw_buffer[20] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Cluster_020_Demand_Percent(uint8 value)
{

    demand_buffer[20] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Cluster_020_Mode(uint8 value)
{

    last_mode[20] = value; ++mode_writes[20];
    return E_OK;
}
Std_ReturnType Rte_Read_Cruise_021_Signal_Raw(uint16 *value)
{
    if (raw_status[21] != E_OK) return raw_status[21];
    *value = raw_buffer[21];
    return E_OK;
}
Std_ReturnType Rte_Impl_Read_Cruise_021_Demand_Percent(uint8 *value)
{
    if (demand_status[21] != E_OK) return demand_status[21];
    *value = demand_buffer[21];
    return E_OK;
}
Std_ReturnType Rte_Write_Cruise_021_Signal_Raw(uint16 value)
{

    raw_buffer[21] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Cruise_021_Demand_Percent(uint8 value)
{

    demand_buffer[21] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Cruise_021_Mode(uint8 value)
{

    last_mode[21] = value; ++mode_writes[21];
    return E_OK;
}
Std_ReturnType Rte_Read_Parking_022_Signal_Raw(uint16 *value)
{
    if (raw_status[22] != E_OK) return raw_status[22];
    *value = raw_buffer[22];
    return E_OK;
}
Std_ReturnType Rte_Read_Parking_022_Demand_Percent(uint8 *value)
{
    if (demand_status[22] != E_OK) return demand_status[22];
    *value = demand_buffer[22];
    return E_OK;
}
Std_ReturnType Rte_Write_Parking_022_Signal_Raw(uint16 value)
{

    raw_buffer[22] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Parking_022_Demand_Percent(uint8 value)
{

    demand_buffer[22] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Parking_022_Mode(uint8 value)
{

    last_mode[22] = value; ++mode_writes[22];
    return E_OK;
}
Std_ReturnType Rte_Read_Charging_023_Signal_Raw(uint16 *value)
{
    if (raw_status[23] != E_OK) return raw_status[23];
    *value = raw_buffer[23];
    return E_OK;
}
Std_ReturnType Rte_Read_Charging_023_Demand_Percent(uint8 *value)
{
    if (demand_status[23] != E_OK) return demand_status[23];
    *value = demand_buffer[23];
    return E_OK;
}
Std_ReturnType Rte_Write_Charging_023_Signal_Raw(uint16 value)
{

    raw_buffer[23] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Charging_023_Demand_Percent(uint8 value)
{

    demand_buffer[23] = value;
    return E_OK;
}
Std_ReturnType Rte_Write_Charging_023_Mode(uint8 value)
{

    last_mode[23] = value; ++mode_writes[23];
    return E_OK;
}

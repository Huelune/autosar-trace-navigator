#include <stdio.h>
#include "../shared/Std_Types.h"
void Brake_000_10ms(void);
void Brake_000_Producer(void);
void Steering_001_10ms(void);
void Steering_001_Producer(void);
void Battery_002_10ms(void);
void Battery_002_Producer(void);
void Thermal_003_10ms(void);
void Thermal_003_Producer(void);
void Lighting_004_10ms(void);
void Lighting_004_Producer(void);
void Door_005_10ms(void);
void Door_005_Producer(void);
void Seat_006_10ms(void);
void Seat_006_Producer(void);
void Wiper_007_10ms(void);
void Wiper_007_Producer(void);
void Cluster_008_10ms(void);
void Cluster_008_Producer(void);
void Cruise_009_10ms(void);
void Cruise_009_Producer(void);
void Parking_010_10ms(void);
void Parking_010_Producer(void);
void Charging_011_10ms(void);
void Charging_011_Producer(void);
void Brake_012_10ms(void);
void Brake_012_Producer(void);
void Steering_013_10ms(void);
void Steering_013_Producer(void);
void Battery_014_10ms(void);
void Battery_014_Producer(void);
void Thermal_015_10ms(void);
void Thermal_015_Producer(void);
void Lighting_016_10ms(void);
void Lighting_016_Producer(void);
void Door_017_10ms(void);
void Door_017_Producer(void);
void Seat_018_10ms(void);
void Seat_018_Producer(void);
void Wiper_019_10ms(void);
void Wiper_019_Producer(void);
void Cluster_020_10ms(void);
void Cluster_020_Producer(void);
void Cruise_021_10ms(void);
void Cruise_021_Producer(void);
void Parking_022_10ms(void);
void Parking_022_Producer(void);
void Charging_023_10ms(void);
void Charging_023_Producer(void);
void Platform_Setup(unsigned int index, uint16 raw, uint8 demand, Std_ReturnType raw_ok, Std_ReturnType demand_ok);
uint8 Platform_Mode(unsigned int index);
unsigned int Platform_Writes(unsigned int index);
typedef struct {
    const char *name;
    unsigned int index;
    uint16 raw;
    uint8 demand;
    Std_ReturnType raw_ok, demand_ok;
    uint8 expected;
    void (*produce)(void);
    void (*consume)(void);
} TestCase;
int main(void)
{
    const TestCase cases[] = {
    {"Brake_000", 0u, 200u, 60u, E_OK, E_OK, MODE_ACTIVE, Brake_000_Producer, Brake_000_10ms},
    {"Brake_000", 0u, 199u, 60u, E_OK, E_OK, MODE_NORMAL, Brake_000_Producer, Brake_000_10ms},
    {"Brake_000", 0u, 200u, 59u, E_OK, E_OK, MODE_NORMAL, Brake_000_Producer, Brake_000_10ms},
    {"Brake_000", 0u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Brake_000_Producer, Brake_000_10ms},
    {"Brake_000", 0u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Brake_000_Producer, Brake_000_10ms},
    {"Brake_000", 0u, 200u, 101u, E_OK, E_OK, MODE_FAULT, Brake_000_Producer, Brake_000_10ms},
    {"Brake_000", 0u, 200u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Brake_000_Producer, Brake_000_10ms},
    {"Brake_000", 0u, 200u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Brake_000_Producer, Brake_000_10ms},
    {"Steering_001", 1u, 250u, 60u, E_OK, E_OK, MODE_ACTIVE, Steering_001_Producer, Steering_001_10ms},
    {"Steering_001", 1u, 249u, 60u, E_OK, E_OK, MODE_NORMAL, Steering_001_Producer, Steering_001_10ms},
    {"Steering_001", 1u, 250u, 59u, E_OK, E_OK, MODE_NORMAL, Steering_001_Producer, Steering_001_10ms},
    {"Steering_001", 1u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Steering_001_Producer, Steering_001_10ms},
    {"Steering_001", 1u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Steering_001_Producer, Steering_001_10ms},
    {"Steering_001", 1u, 250u, 101u, E_OK, E_OK, MODE_FAULT, Steering_001_Producer, Steering_001_10ms},
    {"Steering_001", 1u, 250u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Steering_001_Producer, Steering_001_10ms},
    {"Steering_001", 1u, 250u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Steering_001_Producer, Steering_001_10ms},
    {"Battery_002", 2u, 300u, 60u, E_OK, E_OK, MODE_ACTIVE, Battery_002_Producer, Battery_002_10ms},
    {"Battery_002", 2u, 299u, 60u, E_OK, E_OK, MODE_NORMAL, Battery_002_Producer, Battery_002_10ms},
    {"Battery_002", 2u, 300u, 59u, E_OK, E_OK, MODE_NORMAL, Battery_002_Producer, Battery_002_10ms},
    {"Battery_002", 2u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Battery_002_Producer, Battery_002_10ms},
    {"Battery_002", 2u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Battery_002_Producer, Battery_002_10ms},
    {"Battery_002", 2u, 300u, 101u, E_OK, E_OK, MODE_FAULT, Battery_002_Producer, Battery_002_10ms},
    {"Battery_002", 2u, 300u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Battery_002_Producer, Battery_002_10ms},
    {"Battery_002", 2u, 300u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Battery_002_Producer, Battery_002_10ms},
    {"Thermal_003", 3u, 350u, 60u, E_OK, E_OK, MODE_ACTIVE, Thermal_003_Producer, Thermal_003_10ms},
    {"Thermal_003", 3u, 349u, 60u, E_OK, E_OK, MODE_NORMAL, Thermal_003_Producer, Thermal_003_10ms},
    {"Thermal_003", 3u, 350u, 59u, E_OK, E_OK, MODE_NORMAL, Thermal_003_Producer, Thermal_003_10ms},
    {"Thermal_003", 3u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Thermal_003_Producer, Thermal_003_10ms},
    {"Thermal_003", 3u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Thermal_003_Producer, Thermal_003_10ms},
    {"Thermal_003", 3u, 350u, 101u, E_OK, E_OK, MODE_FAULT, Thermal_003_Producer, Thermal_003_10ms},
    {"Thermal_003", 3u, 350u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Thermal_003_Producer, Thermal_003_10ms},
    {"Thermal_003", 3u, 350u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Thermal_003_Producer, Thermal_003_10ms},
    {"Lighting_004", 4u, 400u, 60u, E_OK, E_OK, MODE_ACTIVE, Lighting_004_Producer, Lighting_004_10ms},
    {"Lighting_004", 4u, 399u, 60u, E_OK, E_OK, MODE_NORMAL, Lighting_004_Producer, Lighting_004_10ms},
    {"Lighting_004", 4u, 400u, 59u, E_OK, E_OK, MODE_NORMAL, Lighting_004_Producer, Lighting_004_10ms},
    {"Lighting_004", 4u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Lighting_004_Producer, Lighting_004_10ms},
    {"Lighting_004", 4u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Lighting_004_Producer, Lighting_004_10ms},
    {"Lighting_004", 4u, 400u, 101u, E_OK, E_OK, MODE_FAULT, Lighting_004_Producer, Lighting_004_10ms},
    {"Lighting_004", 4u, 400u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Lighting_004_Producer, Lighting_004_10ms},
    {"Lighting_004", 4u, 400u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Lighting_004_Producer, Lighting_004_10ms},
    {"Door_005", 5u, 200u, 60u, E_OK, E_OK, MODE_ACTIVE, Door_005_Producer, Door_005_10ms},
    {"Door_005", 5u, 199u, 60u, E_OK, E_OK, MODE_NORMAL, Door_005_Producer, Door_005_10ms},
    {"Door_005", 5u, 200u, 59u, E_OK, E_OK, MODE_NORMAL, Door_005_Producer, Door_005_10ms},
    {"Door_005", 5u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Door_005_Producer, Door_005_10ms},
    {"Door_005", 5u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Door_005_Producer, Door_005_10ms},
    {"Door_005", 5u, 200u, 101u, E_OK, E_OK, MODE_FAULT, Door_005_Producer, Door_005_10ms},
    {"Door_005", 5u, 200u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Door_005_Producer, Door_005_10ms},
    {"Door_005", 5u, 200u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Door_005_Producer, Door_005_10ms},
    {"Seat_006", 6u, 250u, 60u, E_OK, E_OK, MODE_ACTIVE, Seat_006_Producer, Seat_006_10ms},
    {"Seat_006", 6u, 249u, 60u, E_OK, E_OK, MODE_NORMAL, Seat_006_Producer, Seat_006_10ms},
    {"Seat_006", 6u, 250u, 59u, E_OK, E_OK, MODE_NORMAL, Seat_006_Producer, Seat_006_10ms},
    {"Seat_006", 6u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Seat_006_Producer, Seat_006_10ms},
    {"Seat_006", 6u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Seat_006_Producer, Seat_006_10ms},
    {"Seat_006", 6u, 250u, 101u, E_OK, E_OK, MODE_FAULT, Seat_006_Producer, Seat_006_10ms},
    {"Seat_006", 6u, 250u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Seat_006_Producer, Seat_006_10ms},
    {"Seat_006", 6u, 250u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Seat_006_Producer, Seat_006_10ms},
    {"Wiper_007", 7u, 300u, 60u, E_OK, E_OK, MODE_ACTIVE, Wiper_007_Producer, Wiper_007_10ms},
    {"Wiper_007", 7u, 299u, 60u, E_OK, E_OK, MODE_NORMAL, Wiper_007_Producer, Wiper_007_10ms},
    {"Wiper_007", 7u, 300u, 59u, E_OK, E_OK, MODE_NORMAL, Wiper_007_Producer, Wiper_007_10ms},
    {"Wiper_007", 7u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Wiper_007_Producer, Wiper_007_10ms},
    {"Wiper_007", 7u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Wiper_007_Producer, Wiper_007_10ms},
    {"Wiper_007", 7u, 300u, 101u, E_OK, E_OK, MODE_FAULT, Wiper_007_Producer, Wiper_007_10ms},
    {"Wiper_007", 7u, 300u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Wiper_007_Producer, Wiper_007_10ms},
    {"Wiper_007", 7u, 300u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Wiper_007_Producer, Wiper_007_10ms},
    {"Cluster_008", 8u, 350u, 60u, E_OK, E_OK, MODE_ACTIVE, Cluster_008_Producer, Cluster_008_10ms},
    {"Cluster_008", 8u, 349u, 60u, E_OK, E_OK, MODE_NORMAL, Cluster_008_Producer, Cluster_008_10ms},
    {"Cluster_008", 8u, 350u, 59u, E_OK, E_OK, MODE_NORMAL, Cluster_008_Producer, Cluster_008_10ms},
    {"Cluster_008", 8u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Cluster_008_Producer, Cluster_008_10ms},
    {"Cluster_008", 8u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Cluster_008_Producer, Cluster_008_10ms},
    {"Cluster_008", 8u, 350u, 101u, E_OK, E_OK, MODE_FAULT, Cluster_008_Producer, Cluster_008_10ms},
    {"Cluster_008", 8u, 350u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Cluster_008_Producer, Cluster_008_10ms},
    {"Cluster_008", 8u, 350u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Cluster_008_Producer, Cluster_008_10ms},
    {"Cruise_009", 9u, 400u, 60u, E_OK, E_OK, MODE_ACTIVE, Cruise_009_Producer, Cruise_009_10ms},
    {"Cruise_009", 9u, 399u, 60u, E_OK, E_OK, MODE_NORMAL, Cruise_009_Producer, Cruise_009_10ms},
    {"Cruise_009", 9u, 400u, 59u, E_OK, E_OK, MODE_NORMAL, Cruise_009_Producer, Cruise_009_10ms},
    {"Cruise_009", 9u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Cruise_009_Producer, Cruise_009_10ms},
    {"Cruise_009", 9u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Cruise_009_Producer, Cruise_009_10ms},
    {"Cruise_009", 9u, 400u, 101u, E_OK, E_OK, MODE_FAULT, Cruise_009_Producer, Cruise_009_10ms},
    {"Cruise_009", 9u, 400u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Cruise_009_Producer, Cruise_009_10ms},
    {"Cruise_009", 9u, 400u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Cruise_009_Producer, Cruise_009_10ms},
    {"Parking_010", 10u, 200u, 60u, E_OK, E_OK, MODE_ACTIVE, Parking_010_Producer, Parking_010_10ms},
    {"Parking_010", 10u, 199u, 60u, E_OK, E_OK, MODE_NORMAL, Parking_010_Producer, Parking_010_10ms},
    {"Parking_010", 10u, 200u, 59u, E_OK, E_OK, MODE_NORMAL, Parking_010_Producer, Parking_010_10ms},
    {"Parking_010", 10u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Parking_010_Producer, Parking_010_10ms},
    {"Parking_010", 10u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Parking_010_Producer, Parking_010_10ms},
    {"Parking_010", 10u, 200u, 101u, E_OK, E_OK, MODE_FAULT, Parking_010_Producer, Parking_010_10ms},
    {"Parking_010", 10u, 200u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Parking_010_Producer, Parking_010_10ms},
    {"Parking_010", 10u, 200u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Parking_010_Producer, Parking_010_10ms},
    {"Charging_011", 11u, 250u, 60u, E_OK, E_OK, MODE_ACTIVE, Charging_011_Producer, Charging_011_10ms},
    {"Charging_011", 11u, 249u, 60u, E_OK, E_OK, MODE_NORMAL, Charging_011_Producer, Charging_011_10ms},
    {"Charging_011", 11u, 250u, 59u, E_OK, E_OK, MODE_NORMAL, Charging_011_Producer, Charging_011_10ms},
    {"Charging_011", 11u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Charging_011_Producer, Charging_011_10ms},
    {"Charging_011", 11u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Charging_011_Producer, Charging_011_10ms},
    {"Charging_011", 11u, 250u, 101u, E_OK, E_OK, MODE_FAULT, Charging_011_Producer, Charging_011_10ms},
    {"Charging_011", 11u, 250u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Charging_011_Producer, Charging_011_10ms},
    {"Charging_011", 11u, 250u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Charging_011_Producer, Charging_011_10ms},
    {"Brake_012", 12u, 300u, 60u, E_OK, E_OK, MODE_ACTIVE, Brake_012_Producer, Brake_012_10ms},
    {"Brake_012", 12u, 299u, 60u, E_OK, E_OK, MODE_NORMAL, Brake_012_Producer, Brake_012_10ms},
    {"Brake_012", 12u, 300u, 59u, E_OK, E_OK, MODE_NORMAL, Brake_012_Producer, Brake_012_10ms},
    {"Brake_012", 12u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Brake_012_Producer, Brake_012_10ms},
    {"Brake_012", 12u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Brake_012_Producer, Brake_012_10ms},
    {"Brake_012", 12u, 300u, 101u, E_OK, E_OK, MODE_FAULT, Brake_012_Producer, Brake_012_10ms},
    {"Brake_012", 12u, 300u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Brake_012_Producer, Brake_012_10ms},
    {"Brake_012", 12u, 300u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Brake_012_Producer, Brake_012_10ms},
    {"Steering_013", 13u, 350u, 60u, E_OK, E_OK, MODE_ACTIVE, Steering_013_Producer, Steering_013_10ms},
    {"Steering_013", 13u, 349u, 60u, E_OK, E_OK, MODE_NORMAL, Steering_013_Producer, Steering_013_10ms},
    {"Steering_013", 13u, 350u, 59u, E_OK, E_OK, MODE_NORMAL, Steering_013_Producer, Steering_013_10ms},
    {"Steering_013", 13u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Steering_013_Producer, Steering_013_10ms},
    {"Steering_013", 13u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Steering_013_Producer, Steering_013_10ms},
    {"Steering_013", 13u, 350u, 101u, E_OK, E_OK, MODE_FAULT, Steering_013_Producer, Steering_013_10ms},
    {"Steering_013", 13u, 350u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Steering_013_Producer, Steering_013_10ms},
    {"Steering_013", 13u, 350u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Steering_013_Producer, Steering_013_10ms},
    {"Battery_014", 14u, 400u, 60u, E_OK, E_OK, MODE_ACTIVE, Battery_014_Producer, Battery_014_10ms},
    {"Battery_014", 14u, 399u, 60u, E_OK, E_OK, MODE_NORMAL, Battery_014_Producer, Battery_014_10ms},
    {"Battery_014", 14u, 400u, 59u, E_OK, E_OK, MODE_NORMAL, Battery_014_Producer, Battery_014_10ms},
    {"Battery_014", 14u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Battery_014_Producer, Battery_014_10ms},
    {"Battery_014", 14u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Battery_014_Producer, Battery_014_10ms},
    {"Battery_014", 14u, 400u, 101u, E_OK, E_OK, MODE_FAULT, Battery_014_Producer, Battery_014_10ms},
    {"Battery_014", 14u, 400u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Battery_014_Producer, Battery_014_10ms},
    {"Battery_014", 14u, 400u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Battery_014_Producer, Battery_014_10ms},
    {"Thermal_015", 15u, 200u, 60u, E_OK, E_OK, MODE_ACTIVE, Thermal_015_Producer, Thermal_015_10ms},
    {"Thermal_015", 15u, 199u, 60u, E_OK, E_OK, MODE_NORMAL, Thermal_015_Producer, Thermal_015_10ms},
    {"Thermal_015", 15u, 200u, 59u, E_OK, E_OK, MODE_NORMAL, Thermal_015_Producer, Thermal_015_10ms},
    {"Thermal_015", 15u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Thermal_015_Producer, Thermal_015_10ms},
    {"Thermal_015", 15u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Thermal_015_Producer, Thermal_015_10ms},
    {"Thermal_015", 15u, 200u, 101u, E_OK, E_OK, MODE_FAULT, Thermal_015_Producer, Thermal_015_10ms},
    {"Thermal_015", 15u, 200u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Thermal_015_Producer, Thermal_015_10ms},
    {"Thermal_015", 15u, 200u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Thermal_015_Producer, Thermal_015_10ms},
    {"Lighting_016", 16u, 250u, 60u, E_OK, E_OK, MODE_ACTIVE, Lighting_016_Producer, Lighting_016_10ms},
    {"Lighting_016", 16u, 249u, 60u, E_OK, E_OK, MODE_NORMAL, Lighting_016_Producer, Lighting_016_10ms},
    {"Lighting_016", 16u, 250u, 59u, E_OK, E_OK, MODE_NORMAL, Lighting_016_Producer, Lighting_016_10ms},
    {"Lighting_016", 16u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Lighting_016_Producer, Lighting_016_10ms},
    {"Lighting_016", 16u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Lighting_016_Producer, Lighting_016_10ms},
    {"Lighting_016", 16u, 250u, 101u, E_OK, E_OK, MODE_FAULT, Lighting_016_Producer, Lighting_016_10ms},
    {"Lighting_016", 16u, 250u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Lighting_016_Producer, Lighting_016_10ms},
    {"Lighting_016", 16u, 250u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Lighting_016_Producer, Lighting_016_10ms},
    {"Door_017", 17u, 300u, 60u, E_OK, E_OK, MODE_ACTIVE, Door_017_Producer, Door_017_10ms},
    {"Door_017", 17u, 299u, 60u, E_OK, E_OK, MODE_NORMAL, Door_017_Producer, Door_017_10ms},
    {"Door_017", 17u, 300u, 59u, E_OK, E_OK, MODE_NORMAL, Door_017_Producer, Door_017_10ms},
    {"Door_017", 17u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Door_017_Producer, Door_017_10ms},
    {"Door_017", 17u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Door_017_Producer, Door_017_10ms},
    {"Door_017", 17u, 300u, 101u, E_OK, E_OK, MODE_FAULT, Door_017_Producer, Door_017_10ms},
    {"Door_017", 17u, 300u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Door_017_Producer, Door_017_10ms},
    {"Door_017", 17u, 300u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Door_017_Producer, Door_017_10ms},
    {"Seat_018", 18u, 350u, 60u, E_OK, E_OK, MODE_ACTIVE, Seat_018_Producer, Seat_018_10ms},
    {"Seat_018", 18u, 349u, 60u, E_OK, E_OK, MODE_NORMAL, Seat_018_Producer, Seat_018_10ms},
    {"Seat_018", 18u, 350u, 59u, E_OK, E_OK, MODE_NORMAL, Seat_018_Producer, Seat_018_10ms},
    {"Seat_018", 18u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Seat_018_Producer, Seat_018_10ms},
    {"Seat_018", 18u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Seat_018_Producer, Seat_018_10ms},
    {"Seat_018", 18u, 350u, 101u, E_OK, E_OK, MODE_FAULT, Seat_018_Producer, Seat_018_10ms},
    {"Seat_018", 18u, 350u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Seat_018_Producer, Seat_018_10ms},
    {"Seat_018", 18u, 350u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Seat_018_Producer, Seat_018_10ms},
    {"Wiper_019", 19u, 400u, 60u, E_OK, E_OK, MODE_ACTIVE, Wiper_019_Producer, Wiper_019_10ms},
    {"Wiper_019", 19u, 399u, 60u, E_OK, E_OK, MODE_NORMAL, Wiper_019_Producer, Wiper_019_10ms},
    {"Wiper_019", 19u, 400u, 59u, E_OK, E_OK, MODE_NORMAL, Wiper_019_Producer, Wiper_019_10ms},
    {"Wiper_019", 19u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Wiper_019_Producer, Wiper_019_10ms},
    {"Wiper_019", 19u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Wiper_019_Producer, Wiper_019_10ms},
    {"Wiper_019", 19u, 400u, 101u, E_OK, E_OK, MODE_FAULT, Wiper_019_Producer, Wiper_019_10ms},
    {"Wiper_019", 19u, 400u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Wiper_019_Producer, Wiper_019_10ms},
    {"Wiper_019", 19u, 400u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Wiper_019_Producer, Wiper_019_10ms},
    {"Cluster_020", 20u, 200u, 60u, E_OK, E_OK, MODE_ACTIVE, Cluster_020_Producer, Cluster_020_10ms},
    {"Cluster_020", 20u, 199u, 60u, E_OK, E_OK, MODE_NORMAL, Cluster_020_Producer, Cluster_020_10ms},
    {"Cluster_020", 20u, 200u, 59u, E_OK, E_OK, MODE_NORMAL, Cluster_020_Producer, Cluster_020_10ms},
    {"Cluster_020", 20u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Cluster_020_Producer, Cluster_020_10ms},
    {"Cluster_020", 20u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Cluster_020_Producer, Cluster_020_10ms},
    {"Cluster_020", 20u, 200u, 101u, E_OK, E_OK, MODE_FAULT, Cluster_020_Producer, Cluster_020_10ms},
    {"Cluster_020", 20u, 200u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Cluster_020_Producer, Cluster_020_10ms},
    {"Cluster_020", 20u, 200u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Cluster_020_Producer, Cluster_020_10ms},
    {"Cruise_021", 21u, 250u, 60u, E_OK, E_OK, MODE_ACTIVE, Cruise_021_Producer, Cruise_021_10ms},
    {"Cruise_021", 21u, 249u, 60u, E_OK, E_OK, MODE_NORMAL, Cruise_021_Producer, Cruise_021_10ms},
    {"Cruise_021", 21u, 250u, 59u, E_OK, E_OK, MODE_NORMAL, Cruise_021_Producer, Cruise_021_10ms},
    {"Cruise_021", 21u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Cruise_021_Producer, Cruise_021_10ms},
    {"Cruise_021", 21u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Cruise_021_Producer, Cruise_021_10ms},
    {"Cruise_021", 21u, 250u, 101u, E_OK, E_OK, MODE_FAULT, Cruise_021_Producer, Cruise_021_10ms},
    {"Cruise_021", 21u, 250u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Cruise_021_Producer, Cruise_021_10ms},
    {"Cruise_021", 21u, 250u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Cruise_021_Producer, Cruise_021_10ms},
    {"Parking_022", 22u, 300u, 60u, E_OK, E_OK, MODE_ACTIVE, Parking_022_Producer, Parking_022_10ms},
    {"Parking_022", 22u, 299u, 60u, E_OK, E_OK, MODE_NORMAL, Parking_022_Producer, Parking_022_10ms},
    {"Parking_022", 22u, 300u, 59u, E_OK, E_OK, MODE_NORMAL, Parking_022_Producer, Parking_022_10ms},
    {"Parking_022", 22u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Parking_022_Producer, Parking_022_10ms},
    {"Parking_022", 22u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Parking_022_Producer, Parking_022_10ms},
    {"Parking_022", 22u, 300u, 101u, E_OK, E_OK, MODE_FAULT, Parking_022_Producer, Parking_022_10ms},
    {"Parking_022", 22u, 300u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Parking_022_Producer, Parking_022_10ms},
    {"Parking_022", 22u, 300u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Parking_022_Producer, Parking_022_10ms},
    {"Charging_023", 23u, 350u, 60u, E_OK, E_OK, MODE_ACTIVE, Charging_023_Producer, Charging_023_10ms},
    {"Charging_023", 23u, 349u, 60u, E_OK, E_OK, MODE_NORMAL, Charging_023_Producer, Charging_023_10ms},
    {"Charging_023", 23u, 350u, 59u, E_OK, E_OK, MODE_NORMAL, Charging_023_Producer, Charging_023_10ms},
    {"Charging_023", 23u, 2510u, 60u, E_OK, E_OK, MODE_FAULT, Charging_023_Producer, Charging_023_10ms},
    {"Charging_023", 23u, 65535u, 60u, E_OK, E_OK, MODE_FAULT, Charging_023_Producer, Charging_023_10ms},
    {"Charging_023", 23u, 350u, 101u, E_OK, E_OK, MODE_FAULT, Charging_023_Producer, Charging_023_10ms},
    {"Charging_023", 23u, 350u, 60u, E_NOT_OK, E_OK, MODE_FAULT, Charging_023_Producer, Charging_023_10ms},
    {"Charging_023", 23u, 350u, 60u, E_OK, E_NOT_OK, MODE_FAULT, Charging_023_Producer, Charging_023_10ms},
    };
    unsigned int index;
    unsigned int count = (unsigned int)(sizeof(cases) / sizeof(cases[0]));
    for (index = 0u; index < count; ++index) {
        const TestCase *item = &cases[index];
        Platform_Setup(item->index, item->raw, item->demand, item->raw_ok, item->demand_ok);
        item->produce();
        item->consume();
        if (Platform_Mode(item->index) != item->expected || Platform_Writes(item->index) != 1u) {
            fprintf(stderr, "FAIL %s case %u mode=%u\n", item->name, index, (unsigned int)Platform_Mode(item->index));
            return 1;
        }
    }
    printf("PASS large AUTOSAR: %u scenarios\n", count);
    return 0;
}

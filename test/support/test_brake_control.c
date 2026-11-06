#include <stdio.h>
#include "BrakeControl.h"
#include "TestPlatform.h"

typedef struct {
    const char *name;
    uint16 speed;
    uint8 pedal;
    Std_ReturnType speed_status;
    Std_ReturnType pedal_status;
    BrakeMode expected;
} TestCase;

int main(void)
{
    const TestCase cases[] = {
        {"target_exact_threshold", 300u, 60u, E_OK, E_OK, BRAKE_ASSIST},
        {"speed_below_threshold", 299u, 60u, E_OK, E_OK, BRAKE_NORMAL},
        {"pedal_below_threshold", 300u, 59u, E_OK, E_OK, BRAKE_NORMAL},
        {"speed_upper_boundary", 2500u, 100u, E_OK, E_OK, BRAKE_ASSIST},
        {"integer_conversion", 2509u, 60u, E_OK, E_OK, BRAKE_ASSIST},
        {"speed_out_of_range", 2510u, 60u, E_OK, E_OK, BRAKE_FAULT},
        {"speed_invalid_sentinel", 65535u, 60u, E_OK, E_OK, BRAKE_FAULT},
        {"speed_rte_failure", 300u, 60u, E_NOT_OK, E_OK, BRAKE_FAULT},
        {"pedal_rte_failure", 300u, 60u, E_OK, E_NOT_OK, BRAKE_FAULT},
        {"pedal_out_of_range", 300u, 101u, E_OK, E_OK, BRAKE_FAULT},
        {"zero_inputs", 0u, 0u, E_OK, E_OK, BRAKE_NORMAL}
    };
    unsigned int index;
    unsigned int count = (unsigned int)(sizeof(cases) / sizeof(cases[0]));

    for (index = 0u; index < count; ++index) {
        const TestCase *item = &cases[index];
        TestPlatform_Reset(item->speed, item->pedal,
                           item->speed_status, item->pedal_status);
        SensorAcquisition_10ms();
        BrakeControl_10ms();
        if ((TestPlatform_LastMode() != (uint8)item->expected) ||
            (TestPlatform_ModeWrites() != 1u)) {
            fprintf(stderr, "FAIL %s: mode=%u writes=%u\n", item->name,
                    (unsigned int)TestPlatform_LastMode(), TestPlatform_ModeWrites());
            return 1;
        }
        printf("PASS %s\n", item->name);
    }

    /* Verify a new producer cycle replaces data used by the consumer. */
    TestPlatform_Reset(300u, 60u, E_OK, E_OK);
    BrakeControl_10ms(); /* Producer has not run: buffers still contain zero. */
    if (TestPlatform_LastMode() != (uint8)BRAKE_NORMAL) {
        return 1;
    }
    SensorAcquisition_10ms();
    BrakeControl_10ms();
    if ((TestPlatform_LastMode() != (uint8)BRAKE_ASSIST) ||
        (TestPlatform_ModeWrites() != 2u)) {
        return 1;
    }
    puts("PASS producer_consumer_order");
    printf("PASS all %u scenarios\n", count + 1u);
    return 0;
}

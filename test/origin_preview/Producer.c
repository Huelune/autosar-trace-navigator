#include "Origins.h"
unsigned Preview_Raw;
unsigned Preview_Enable;
unsigned Preview_Quality;
static unsigned Preview_Hidden;
const unsigned Preview_Locked = 4u;
unsigned Origin_Hidden(void) { return Preview_Hidden + Preview_Locked; }
void Origin_Publish(void)
{
    unsigned converted = 0u;
    if (Preview_Enable != 0u) {
        if (Preview_Quality == 1u) {
            converted = Preview_Raw * 2u;
        } else if (Preview_Quality == 2u) {
            converted = Preview_Raw + 10u;
        }
        (void)Rte_Write_Preview_Pedal(converted);
    }
}

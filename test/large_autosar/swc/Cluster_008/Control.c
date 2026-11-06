#include "Cluster_008.h"
#include "Rte_Cluster_008.h"
void Cluster_008_10ms(void)
{
    int mode = Cluster_008_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Cluster_008_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Cluster_008_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Cluster_008_Mode((uint8)MODE_NORMAL);
    }
}
int Cluster_008_Evaluate(void)
{
    int request = Cluster_008_Decide();
    if (request < 0) {
        (void)Cluster_008_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

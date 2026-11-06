#include "Cluster_020.h"
#include "Rte_Cluster_020.h"
void Cluster_020_10ms(void)
{
    int mode = Cluster_020_Evaluate();
    if (mode == MODE_FAULT) {
        (void)Rte_Write_Cluster_020_Mode((uint8)MODE_FAULT);
    } else if (mode == MODE_ACTIVE) {
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_Cluster_020_Mode((uint8)MODE_ACTIVE);
    } else {
        (void)Rte_Write_Cluster_020_Mode((uint8)MODE_NORMAL);
    }
}
int Cluster_020_Evaluate(void)
{
    int request = Cluster_020_Decide();
    if (request < 0) {
        (void)Cluster_020_Diagnostic(request);
        return MODE_FAULT;
    } else if (request == 1) {
        return MODE_ACTIVE;
    } else {
        return MODE_NORMAL;
    }
}

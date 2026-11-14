#include "Callers.h"
unsigned Caller_Raw;
unsigned Caller_AlternateRaw;
unsigned Caller_Enable;

int Caller_Check(unsigned ignored, unsigned pedal)
{
    (void)ignored;
    if (pedal >= 60u) { return 1; }
    return 0;
}
void Caller_Relay(unsigned command)
{
    (void)Caller_Check(999u, command);
}
void Caller_Run(void)
{
    if (Caller_Enable != 0u) {
        unsigned amount = Caller_Raw * 2u;
        Caller_Relay(amount);
    }
}
void Caller_Alternate(void)
{
    (void)Caller_Check(0u, Caller_AlternateRaw + 10u);
}
void Caller_Literal(void)
{
    (void)Caller_Check(7u, 65u);
}
unsigned Caller_GetRaw(void)
{
    return Caller_Raw;
}
void Caller_FromFunction(void)
{
    (void)Caller_Check(123u, Caller_GetRaw());
}

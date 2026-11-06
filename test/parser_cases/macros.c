#define SCALE(x) ((x) / 10)
#define READY 1
#if FEATURE
int Select(void) { return SCALE(300); }
#else
int Select(void) { return 0; }
#endif
int Decide(void)
{
    if (READY) return HEADER_MACRO(1);
    return 0;
}

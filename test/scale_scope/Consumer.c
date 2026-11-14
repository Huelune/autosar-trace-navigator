/* Synthetic scope fixture: the supplier lives in another directory. */
int Supply(void);
int Consumer(void)
{
    int value = Supply();
    return value;
}

int Callee(void)
{
    return 1;
}

int Caller(void)
{
    /* 한글😀 */ return Callee();
}

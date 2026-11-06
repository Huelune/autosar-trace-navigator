/* Synthetic parser fixture: statements, comments and lexical nesting. */
int Check(int value);
void Run(int x)
{
    if (Check(x)) {
        if (x > 10) First();
        else Second();
    } else /* between else and if */ if (x == 0) {
        Third();
    } else {
        if (x < 0) Fourth();
    }
    Done();
}

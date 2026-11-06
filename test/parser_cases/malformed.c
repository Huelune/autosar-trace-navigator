/* Deliberately invalid; must produce uncertainty, not a clean success. */
int Broken(void) {
    if (1) {
        return 0;

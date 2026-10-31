/* The plugin's search, run on the real BrgGame-Steam.exe (mapped as a file,
 * nothing runs). Every piece must be found exactly once. Only run by
 * `build.py --exe PATH`: the game is not part of this repository. */
#define LID_BETTERDUSTIN5_NO_DLLMAIN
#include "../dll/lid_betterdustin5.c"

#include <stdio.h>

static unsigned long long rva(void *p, unsigned char *base)
{
    return p ? (unsigned long long)((unsigned char *)p - base) : 0ULL;
}

int main(int argc, char **argv)
{
    struct pieces pc;
    unsigned char *base;
    HMODULE m;
    int fails = 0;

    if (argc < 2) { puts("usage: realexe PATH-TO-BrgGame-Steam.exe"); return 2; }
    m = LoadLibraryExA(argv[1], NULL, LOAD_LIBRARY_AS_IMAGE_RESOURCE | LOAD_LIBRARY_AS_DATAFILE);
    if (!m) { printf("could not map %s (error %lu)\n", argv[1], GetLastError()); return 2; }
    base = (unsigned char *)((ULONG_PTR)m & ~(ULONG_PTR)3);

    find_pieces(base, &pc);
    /* where they are in game build 5.0.5.0 (1.92) */
    printf("paid Dustin5 item check %-7s game+0x%llX (1.92: game+0x126CD71)\n",
           pc.cap ? "found" : "MISSING", rva(pc.cap, base));
    printf("Rewards Box receive call %-7s game+0x%llX (1.92: game+0x1162130)\n",
           pc.receive_site ? "found" : "MISSING", rva(pc.receive_site, base));
    printf("  the receive function   %-7s game+0x%llX (1.92: game+0x13517D0), %d call(s) to it (needs 1)\n",
           pc.receive_fn ? "found" : "MISSING", rva(pc.receive_fn, base), pc.receive_calls);
    if (!pc.cap)
        fails++;
    if (!pc.receive_site)
        fails++;
    printf(fails ? "\n%d FAILED\n" : "\nall found\n", fails);
    return fails != 0;
}

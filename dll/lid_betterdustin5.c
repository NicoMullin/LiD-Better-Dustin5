/*
 * lid-betterdustin5.dll for Let It Die - a plugin for the LiD Plugin Loader,
 * for the Better Dustin5 mod. It changes game code in memory only.
 *
 * The game's built-in offline server answers Dustin5 (the DustShooter) and
 * the Rewards Box. The plugin makes two changes to it:
 *
 *   - Items a send. A paid Dustin5 ("CHARGE") refuses more than 5 items in
 *     one send: `cmp r8d,5` in its handler. The plugin puts
 *     master_const_int LID_DUSTIN_ITEMS there instead, when the mod has
 *     written it. A free Dustin5 has no such check. (The menu's own limit is
 *     BrgUIMenu_DustShooter.mCheckMax, which the mod sets in the game's UI
 *     settings file.)
 *   - Rewards Box to the Storage Box. Taking a present runs the server's
 *     receive function with no storage named, which means the Death Bag; the
 *     same function takes "coin_locker", the Storage Box, as well. The mod's
 *     change to the Rewards Box marks the presents to send to storage with an
 *     "@" before their id. The plugin takes the one call to the receive
 *     function: for a marked present it passes the id without the "@" and
 *     "coin_locker"; every other present goes through as it always did.
 *
 * Safety rules:
 *   - Each piece of game code is found by its exact bytes, exactly once, or
 *     that part changes nothing (the log says which).
 *   - Changed in the game: one byte (the 5), one 5-byte call and a 12-byte
 *     stub in a page of its own.
 *   - masters.db is opened read-only. No network, no registry. It writes only
 *     lid-betterdustin5.log next to itself.
 *   - Delete lid-betterdustin5.dll and the game is stock again (the mod's
 *     Rewards Box change needs it for storage, so the two go together).
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "sqlite3.h"
#include "version.h"

/* ------------------------------------------------------------------ log */

static wchar_t g_log_path[MAX_PATH];
static int g_log_started;

static void log_line(const char *fmt, ...)
{
    char msg[1024];
    SYSTEMTIME t;
    va_list ap;
    int n;
    HANDLE f;
    DWORD written;

    if (!g_log_path[0])
        return;
    GetLocalTime(&t);
    n = snprintf(msg, sizeof msg, "%02u:%02u:%02u  ", t.wHour, t.wMinute, t.wSecond);
    va_start(ap, fmt);
    n += vsnprintf(msg + n, sizeof msg - n - 2, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof msg - 3)
        n = (int)sizeof msg - 3;
    msg[n++] = '\r';
    msg[n++] = '\n';

    /* a fresh log each time the game starts */
    f = CreateFileW(g_log_path, g_log_started ? FILE_APPEND_DATA : GENERIC_WRITE,
                    FILE_SHARE_READ, NULL, g_log_started ? OPEN_ALWAYS : CREATE_ALWAYS,
                    FILE_ATTRIBUTE_NORMAL, NULL);
    if (f == INVALID_HANDLE_VALUE)
        return;
    g_log_started = 1;
    WriteFile(f, msg, (DWORD)n, &written, NULL);
    CloseHandle(f);
}

/* ------------------------------------------------------------ helpers */

struct span {
    unsigned char *start;
    size_t size;
};

static int section(unsigned char *base, const char *name, struct span *out)
{
    IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
    IMAGE_NT_HEADERS64 *nt;
    IMAGE_SECTION_HEADER *sec;
    WORD i;

    if (dos->e_magic != IMAGE_DOS_SIGNATURE)
        return 0;
    nt = (IMAGE_NT_HEADERS64 *)(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE)
        return 0;
    sec = IMAGE_FIRST_SECTION(nt);
    for (i = 0; i < nt->FileHeader.NumberOfSections; i++, sec++) {
        if (strncmp((const char *)sec->Name, name, IMAGE_SIZEOF_SHORT_NAME) == 0) {
            out->start = base + sec->VirtualAddress;
            out->size = sec->Misc.VirtualSize;
            return 1;
        }
    }
    return 0;
}

static int32_t rd32(const unsigned char *p)
{
    int32_t v;
    memcpy(&v, p, 4);
    return v;
}

static unsigned char *call_target(unsigned char *call)
{
    return call + 5 + rd32(call + 1);
}

/* A byte pattern like "48 8B 0D ?? ?? ?? ?? E8", found exactly once in `s`. */
static unsigned char *find_once(struct span s, const char *pattern)
{
    unsigned char bytes[160], mask[160];
    int n = 0, first = -1, k;
    const char *c = pattern;
    unsigned char *p, *end, *hit = NULL;

    while (*c && n < (int)sizeof bytes) {
        while (*c == ' ')
            c++;
        if (!*c)
            break;
        if (c[0] == '?') {
            mask[n] = 0;
            bytes[n] = 0;
        } else {
            unsigned v = 0;
            sscanf(c, "%2x", &v);
            mask[n] = 1;
            bytes[n] = (unsigned char)v;
            if (first < 0)
                first = n;
        }
        n++;
        c += 2;
    }
    if (first < 0 || (size_t)n > s.size)
        return NULL;
    end = s.start + s.size - n;
    for (p = s.start + first; p <= end + first; p++) {
        p = memchr(p, bytes[first], (size_t)(end + first - p) + 1);
        if (!p)
            break;
        for (k = 0; k < n; k++)
            if (mask[k] && p[k - first] != bytes[k])
                break;
        if (k == n) {
            if (hit)
                return NULL;        /* twice: not the code we know */
            hit = p - first;
        }
    }
    return hit;
}

static int write_code(unsigned char *at, const void *bytes, size_t n)
{
    DWORD old;
    if (!VirtualProtect(at, n, PAGE_EXECUTE_READWRITE, &old))
        return 0;
    memcpy(at, bytes, n);
    VirtualProtect(at, n, old, &old);
    FlushInstructionCache(GetCurrentProcess(), at, n);
    return 1;
}

/* --------------------------------------------------------- the pieces */

/* The paid Dustin5's item check in the server's DustShooter handler (after
 * "dustshooter invalid type"): mov r8d,[r13+8] (the items sent) / cmp r8d,5 /
 * jle ok / lea rdx,"dustshooter capacity over: %d". */
static const char CAP_PATTERN[] = "45 8B 45 08 41 83 F8 05 7E 3D 48 8D 15";
#define CAP_AT 7            /* the 5 */
#define STOCK_CAP 5

/* The Rewards Box handler's call for a "receive": lea rdx,"" (when the id is
 * empty) / xor r8d,r8d (no storage named: the Death Bag) / lea rcx,server /
 * call receive / jmp next / mov eax,[rbx+8] / test eax,eax ("remove" next). */
static const char RECEIVE_PATTERN[] =
    "48 8D 15 ?? ?? ?? ?? 45 33 C0 48 8D 0D ?? ?? ?? ?? E8 ?? ?? ?? ?? E9 8E 00 00 00 8B 43 08 85 C0";
#define RECEIVE_CALL_AT 17

struct pieces {
    unsigned char *base;
    struct span text;
    unsigned char *cap;             /* the 5 */
    unsigned char *receive_site;    /* the call */
    unsigned char *receive_fn;      /* what it calls */
    int receive_calls;              /* calls to that function in the game (needs 1) */
};

static struct pieces g_pc;

/* Find everything, without changing anything. `base` is the game's exe in
 * memory (the tests pass a mapped copy instead). */
static void find_pieces(unsigned char *base, struct pieces *pc)
{
    unsigned char *p;
    size_t i;

    memset(pc, 0, sizeof *pc);
    pc->base = base;
    if (!section(base, ".text", &pc->text))
        return;
    p = find_once(pc->text, CAP_PATTERN);
    if (p && p[CAP_AT] == STOCK_CAP)
        pc->cap = p + CAP_AT;
    p = find_once(pc->text, RECEIVE_PATTERN);
    if (p) {
        pc->receive_fn = call_target(p + RECEIVE_CALL_AT);
        for (i = 0; i + 5 <= pc->text.size; i++) {
            unsigned char *c = pc->text.start + i;
            if (c[0] == 0xE8 && call_target(c) == pc->receive_fn)
                pc->receive_calls++;
        }
        if (pc->receive_calls == 1)
            pc->receive_site = p + RECEIVE_CALL_AT;
        else
            pc->receive_fn = NULL;
    }
}

/* ------------------------------------------------------- the settings */

static char g_db_path[MAX_PATH * 3];

/* masters.db, two folders above the exe (Binaries\Win64). */
static int db_path(void)
{
    wchar_t exe[MAX_PATH], path[MAX_PATH], *slash;
    DWORD n = GetModuleFileNameW(NULL, exe, MAX_PATH);

    if (n == 0 || n >= MAX_PATH)
        return 0;
    slash = wcsrchr(exe, L'\\');
    if (!slash || (size_t)(slash - exe) + 40 >= MAX_PATH)
        return 0;
    wcscpy(slash + 1, L"..\\..\\BrgGame\\Content\\masters.db");
    if (!GetFullPathNameW(exe, MAX_PATH, path, NULL))
        return 0;
    return WideCharToMultiByte(CP_UTF8, 0, path, -1, g_db_path, sizeof g_db_path, NULL, NULL) > 0;
}

/* master_const_int LID_DUSTIN_ITEMS, 1 to 127, or 0 when it is not there. */
static int read_items(void)
{
    sqlite3 *db = NULL;
    sqlite3_stmt *st = NULL;
    int items = 0;

    if (!g_db_path[0] && !db_path()) {
        log_line("could not work out where masters.db is");
        return 0;
    }
    if (sqlite3_open_v2(g_db_path, &db, SQLITE_OPEN_READONLY, NULL) != SQLITE_OK) {
        log_line("could not open %s (%s)", g_db_path, db ? sqlite3_errmsg(db) : "out of memory");
        sqlite3_close(db);
        return 0;
    }
    sqlite3_busy_timeout(db, 2000);
    if (sqlite3_prepare_v2(db, "SELECT value FROM master_const_int WHERE id = 'LID_DUSTIN_ITEMS'",
                           -1, &st, NULL) == SQLITE_OK) {
        if (sqlite3_step(st) == SQLITE_ROW)
            items = sqlite3_column_int(st, 0);
        sqlite3_finalize(st);
    }
    sqlite3_close(db);
    if (items < 0)
        items = 0;
    if (items > 127)        /* the check holds a signed byte */
        items = 127;
    return items;
}

/* ------------------------------------------------- the storage stub */

typedef uint64_t (*receive_fn)(void *server, const wchar_t *pid, const wchar_t *storage);
static receive_fn g_receive;

/* A present marked for the Storage Box: its id with an "@" in front. Each
 * one is logged with how it went (the first STORAGE_LOGGED of them), so a
 * test shows what Triangle and L1 really sent. */
#define STORAGE_LOGGED 300
static uint64_t receive_hook(void *server, const wchar_t *pid, const wchar_t *storage)
{
    static int sent, failed;
    uint64_t r;

    if (!pid || pid[0] != L'@')
        return g_receive(server, pid, storage);
    r = g_receive(server, pid + 1, L"coin_locker");
    sent++;
    if (!(char)r)
        failed++;
    if (sent <= STORAGE_LOGGED)
        log_line("storage: present %ls %s (%d sent there so far, %d refused)", pid + 1,
                 (char)r ? "is in the Storage Box" : "was REFUSED by the game", sent, failed);
    return r;
}

/* One page within 2 GB of the game code, for the stub. */
static unsigned char *page_near(unsigned char *code)
{
    const ULONG_PTR step = 0x10000;
    ULONG_PTR origin = (ULONG_PTR)code & ~(step - 1);
    ULONG_PTR d;

    for (d = step; d < 0x70000000; d += step) {
        void *p = VirtualAlloc((void *)(origin - d), 4096, MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE);
        if (!p)
            p = VirtualAlloc((void *)(origin + d), 4096, MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE);
        if (p)
            return p;
    }
    return NULL;
}

static int hook_receive(void)
{
    unsigned char stub[12], call[5] = {0xE8}, *page;
    void *target = (void *)receive_hook;
    intptr_t d;
    int32_t r;

    page = page_near(g_pc.receive_site);
    if (!page)
        return 0;
    d = page - (g_pc.receive_site + 5);
    if (d != (int32_t)d) {
        VirtualFree(page, 0, MEM_RELEASE);
        return 0;
    }
    stub[0] = 0x48; stub[1] = 0xB8; memcpy(stub + 2, &target, 8);   /* mov rax,receive_hook */
    stub[10] = 0xFF; stub[11] = 0xE0;                               /* jmp rax */
    memcpy(page, stub, sizeof stub);
    FlushInstructionCache(GetCurrentProcess(), page, sizeof stub);
    g_receive = (receive_fn)g_pc.receive_fn;
    r = (int32_t)d;
    memcpy(call + 1, &r, 4);
    if (!write_code(g_pc.receive_site, call, sizeof call)) {
        VirtualFree(page, 0, MEM_RELEASE);
        return 0;
    }
    return 1;
}

static void patch_game(void)
{
    unsigned char *base = (unsigned char *)GetModuleHandleW(NULL);
    int items;

    find_pieces(base, &g_pc);

    if (!g_pc.cap) {
        log_line("the paid Dustin5's item check was not found exactly once - nothing changed there. "
                 "A game update may have moved it.");
    } else if ((items = read_items()) == 0) {
        log_line("no LID_DUSTIN_ITEMS in masters.db - a paid Dustin5 takes 5 items, as the game has it");
    } else {
        unsigned char v = (unsigned char)items;
        if (v != STOCK_CAP && !write_code(g_pc.cap, &v, 1))
            log_line("could not change the paid Dustin5's item check");
        else
            log_line("items: ready - a paid Dustin5 takes up to %d items a send (game+0x%llX)", items,
                     (unsigned long long)(g_pc.cap - base));
    }

    if (!g_pc.receive_site) {
        log_line("the Rewards Box's receive call was not found exactly once (call %d, calls to it %d) - "
                 "nothing changed there, so presents cannot go to the Storage Box. A game update may have "
                 "moved it.", g_pc.receive_fn != NULL || g_pc.receive_calls > 0, g_pc.receive_calls);
    } else if (!hook_receive()) {
        log_line("could not change the Rewards Box's receive call - nothing changed there");
    } else {
        log_line("storage: ready - presents marked for the Storage Box go there (game+0x%llX)",
                 (unsigned long long)(g_pc.receive_site - base));
    }
}

/* ---------------------------------------------------------------- start */

static int running_in_the_game(void)
{
    wchar_t exe[MAX_PATH];
    const wchar_t *name;
    DWORD n = GetModuleFileNameW(NULL, exe, MAX_PATH);

    if (n == 0 || n >= MAX_PATH)
        return 0;
    name = wcsrchr(exe, L'\\');
    name = name ? name + 1 : exe;
    return _wcsicmp(name, L"BrgGame-Steam.exe") == 0;
}

static void own_paths(HINSTANCE inst)
{
    wchar_t *slash;
    DWORD n = GetModuleFileNameW(inst, g_log_path, MAX_PATH);

    slash = (n && n < MAX_PATH - 24) ? wcsrchr(g_log_path, L'\\') : NULL;
    if (!slash) {
        g_log_path[0] = 0;
        return;
    }
    wcscpy(slash + 1, L"lid-betterdustin5.log");
}

#ifndef LID_BETTERDUSTIN5_NO_DLLMAIN
BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(inst);
        own_paths(inst);
        if (!running_in_the_game())
            return TRUE;    /* some other program - change nothing */
        log_line("LiD Better Dustin5 lid-betterdustin5.dll " LID_DLL_VERSION " loaded");
        patch_game();
    }
    return TRUE;
}
#endif

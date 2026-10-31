/* The plugin's own logic, without the game: the setting it reads from a test
 * masters.db, and what its receive stub hands the server's receive function.
 *
 * build.py makes the test masters.db next to this exe (BrgGame\Content two
 * folders up, as in the game) with master_const_int LID_DUSTIN_ITEMS = 40. */
#define LID_BETTERDUSTIN5_NO_DLLMAIN
#include "../dll/lid_betterdustin5.c"

#include <stdio.h>

static int fails;
static const wchar_t *g_got_pid, *g_got_storage;
static void *g_got_server;

static void check(int ok, const char *what)
{
    printf("%s  %s\n", ok ? "ok  " : "FAIL", what);
    fails += !ok;
}

static uint64_t fake_receive(void *server, const wchar_t *pid, const wchar_t *storage)
{
    g_got_server = server;
    g_got_pid = pid;
    g_got_storage = storage;
    return 1;
}

static void set_items(const char *sql)
{
    sqlite3 *db;
    if (sqlite3_open_v2(g_db_path, &db, SQLITE_OPEN_READWRITE, NULL) == SQLITE_OK) {
        sqlite3_exec(db, sql, NULL, NULL, NULL);
        sqlite3_close(db);
    }
}

int main(void)
{
    int server = 0;

    /* the setting */
    check(read_items() == 40, "LID_DUSTIN_ITEMS is read from masters.db");
    set_items("UPDATE master_const_int SET value = 500 WHERE id = 'LID_DUSTIN_ITEMS'");
    check(read_items() == 127, "more than a signed byte holds is kept to 127");
    set_items("DELETE FROM master_const_int WHERE id = 'LID_DUSTIN_ITEMS'");
    check(read_items() == 0, "no row: 0, so the game's own 5 stays");

    /* the receive stub */
    g_receive = fake_receive;
    receive_hook(&server, L"PRESENT_1", NULL);
    check(g_got_server == &server && wcscmp(g_got_pid, L"PRESENT_1") == 0 && g_got_storage == NULL,
          "an ordinary present goes through unchanged, to the Death Bag");
    receive_hook(&server, L"@PRESENT_2", NULL);
    check(wcscmp(g_got_pid, L"PRESENT_2") == 0 && g_got_storage && wcscmp(g_got_storage, L"coin_locker") == 0,
          "a present marked with @ goes to the Storage Box (coin_locker), without the @");
    receive_hook(&server, L"", NULL);
    check(g_got_pid && g_got_pid[0] == 0 && g_got_storage == NULL, "an empty id goes through unchanged");
    receive_hook(&server, NULL, NULL);
    check(g_got_pid == NULL && g_got_storage == NULL, "no id at all goes through unchanged");

    /* the patterns are well formed (a typo would make find_once miss) */
    check(strlen(CAP_PATTERN) == 13 * 3 - 1, "the item check pattern is 13 bytes");
    check(strlen(RECEIVE_PATTERN) == 32 * 3 - 1, "the receive call pattern is 32 bytes");
    check(memcmp(RECEIVE_PATTERN + RECEIVE_CALL_AT * 3, "E8", 2) == 0, "the call is where RECEIVE_CALL_AT says");

    printf(fails ? "\n%d FAILED\n" : "\nall passed\n", fails);
    return fails != 0;
}

# LiD Better Dustin5

Dustin5 and the Rewards Box made easier in LET IT DIE (Steam, offline): every
Dustin5 free with no 5-item limit, no waiting at Dustin5, and a Rewards Box
that can send presents to the Storage Box or hand out everything at once.

- **Better Dustin5** (`mods/Better Dustin5`): the mod for the LET IT DIE DB Mod
  Manager - the settings, the database changes and two changes to
  `BrgGame.upk`.
- **lid-betterdustin5.dll** (`dll/`): a plugin for the
  [LiD Plugin Loader](https://github.com/NicoMullin/LiD-Plugin-Loader) for the
  two things only the game's server can do.

## What you get

Set it in the manager, on the Better Dustin5 mod's **Configuration** tab:

| Setting                                         | Default  | You can choose                         |
|-------------------------------------------------|----------|----------------------------------------|
| Every Dustin5 is free                           | On       | Off: paid ones stay paid               |
| Price of a paid send                            | 5,000 KC | 1 to 200,000 KC                        |
| Items a paid send                               | 20       | 1 to 70 (the game's own is 5)          |
| No waiting at Dustin5                           | On       | Off                                    |
| Rewards Box: Storage Box and take everything    | On       | Off                                    |

In the Rewards Box, with the last one on:

| Button   | What it does                                       |
|----------|----------------------------------------------------|
| Triangle | Send the picked present to the Storage Box         |
| L1       | Send everything that fits there                    |
| R1       | Take everything that fits                          |

Each asks Yes/No first, and the button guide shows all three.

Weapons, armour, items, mushrooms and beasts go to the Storage Box; Kill Coins,
decals and the rest go where they always go. What does not fit stays in the box.

## How it works

**Dustin5.** The Tower has two kinds of DustShooter: `CHARGE`, which costs
`PRD_DUSTSHOOT` (5,000 KC) and takes at most 5 items, and `FREE`, which costs
nothing and has no limit. Which kind each one is lives in `master_dustshooter`.
Both the menu and the game's built-in offline server enforce the paid kind's 5:

- the menu reads `BrgUIMenu_DustShooter.mCheckMax` from the game's UI settings
  (`SteamPCRelease-BrgUI.ini`), which the mod sets;
- the server's DustShooter handler refuses more with `cmp r8d,5`. The plugin
  puts `master_const_int` `LID_DUSTIN_ITEMS` there.

**No waiting.** The menu opens once your fighter has "looked at Dustin", or
after 5 seconds; after a send it waits for Dustin5 to be idle again, after its
animation and your fighter's. The mod's `BrgGame.upk` change sets the "looked"
flag as the menu opens and starts neither animation, so Dustin5 stays idle.

**The Rewards Box.** The box keeps what you do in a queue (take or delete, up
to 100) and sends it to the server when you close it. The mod's `BrgGame.upk`
change adds Triangle, L1 and R1 to its list and queues the presents for them
itself, checking the Death Bag (as the game does) and the Storage Box's free
slots. A present for the Storage Box is sent as a take of `@` plus its id.

The server's receive function already takes a place to put a present -
`death_bag`, or `coin_locker` (the Storage Box) - but the Rewards Box never
names one, so it is always the Death Bag. The plugin takes the one call to it:
for an id starting with `@` it passes the id without the `@` and
`coin_locker`; everything else goes through as before.

The game keeps its own copy of the Storage Box, rebuilt only from a Storage Box
reply (putting in, taking out, sorting); the Rewards Box's reply carries none.
So the mod's change also has the Storage Box ask for its contents as it opens:
its take-out step with nothing picked, whose reply holds the whole Storage Box,
and then its main menu, as after any take-out. What arrived shows at once.

Safety:

- Every piece of game code is found by its exact bytes, exactly once, or that
  part changes nothing and `lid-betterdustin5.log` says so.
- Changed in the game: one byte (the 5), and one 5-byte call (plus a 12-byte
  stub).
- `masters.db` is opened read-only. No network, no registry. It writes only
  `lid-betterdustin5.log` next to itself.
- The `BrgGame.upk` changes are package patches: they hold only the changed
  functions, name every object they use, and stack with the manager's other
  `BrgGame.upk` mods.

## Why the DLL is built by GitHub

A DLL can do anything, so you should not have to take one on trust. Every
release on this page is built by GitHub Actions from the source in this
repository, on GitHub's own machines, and the tests run before anything is
published. You can check the DLL in two ways:

1. **Signed build record.** Each release DLL has an attestation: a signed
   record, kept by GitHub, of the exact workflow run and commit that built it.
   With the [GitHub CLI](https://cli.github.com/):

   ```
   gh attestation verify lid-betterdustin5.dll --repo NicoMullin/LiD-Better-Dustin5
   ```

2. **Rebuild it yourself.** The build is reproducible: the same source and the
   same compiler give a byte-identical file. See
   [Building it yourself](#building-it-yourself) and compare the SHA-256 with
   the one on the release page.

## Installing

**The easy way.** In the LET IT DIE DB Mod Manager, close the game, click
**Get mods...** and then **Get** next to **Better Dustin5**. It downloads this
repository's newest release, checks it against the SHA-256 GitHub lists for
it, and once you say yes adds the mod and puts `lid-betterdustin5.dll` in the
game's `Binaries\Win64\lid-plugins` - with the
[LiD Plugin Loader](https://github.com/NicoMullin/LiD-Plugin-Loader) too, if
you do not have it yet. Then tick **Better Dustin5** and click **Save Mod
List**. The plugin is switched on and off with the mod.

**By hand.**

1. Install the [LiD Plugin Loader](https://github.com/NicoMullin/LiD-Plugin-Loader)
   once, if you have not already.
2. Download `LiD-Better-Dustin5.zip` from the
   [latest release](https://github.com/NicoMullin/LiD-Better-Dustin5/releases/latest).
   Put `lid-plugins\lid-betterdustin5.dll` from it in the game's
   `Binaries\Win64\lid-plugins`, and drop `mods\Better Dustin5` on the mod
   manager's window.

## Building it yourself

You need Windows and Python 3. The compiler is Zig, installed with pip; no
Visual Studio needed.

```
py -3 -m pip install ziglang==0.16.0
py -3 build.py --test
```

The DLL lands in `out\lid-betterdustin5.dll` and the SHA-256 is printed at
the end. Use Zig 0.16.0 exactly: another version builds a working DLL, but not
a byte-identical one.

The plugin reads `masters.db` with [SQLite](https://www.sqlite.org/) (public
domain). Its source is not kept here: the first build downloads the official
amalgamation (3.53.4) from sqlite.org into `third_party\` and refuses it unless
its SHA3-256 matches the one sqlite.org publishes.

`--test` runs the plugin's own code against a small `masters.db` and checks
the item count it reads, and that its stub sends a present marked with `@` to
the Storage Box and every other present through unchanged. With none of the
game code, nothing is changed and the log says so.

`--exe PATH\BrgGame-Steam.exe` also runs `tests/realexe.c`: the plugin's own
search on the real game file (mapped, not run), which must find every piece.
The game is not in this repository, so GitHub does not run it.

The mod's `BrgGame.upk` changes are written by a tool that reads the game's
stock package (never changing it) and needs a LET IT DIE DB Mod Manager
checkout for its package reader:

```
py -3 tools/build_better_dustin5.py --manager PATH\TO\LiD-DB-Editor --upk PATH\TO\stock\BrgGame.upk
```

## Making a release

1. Set the new version in [dll/version.h](dll/version.h).
2. Push a tag with the same version, for example `v0.1.0`.

GitHub builds, tests and publishes the release. The build stops if the tag and
`version.h` don't match.

## License

MIT - see [LICENSE](LICENSE). Made by KSFA.

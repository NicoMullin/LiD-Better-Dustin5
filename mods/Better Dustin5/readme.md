# Better Dustin5

Dustin5 and the Rewards Box, made easier. Set each part in **Configuration**.

## Sending home with Dustin5

| Setting                   | Default  | What it does                                                    |
|---------------------------|----------|-----------------------------------------------------------------|
| **Every Dustin5 is free** | On       | Every Dustin5 in the Tower is a free one: nothing to pay, and as many items a send as you like |
| **Price of a paid send**  | 5,000 KC | With the above off: what a paid Dustin5 charges (1 to 200,000 KC) |
| **Items a paid send**     | 20       | With the above off: how many items a paid Dustin5 takes (1 to 70; the game's own is 5) |

The Tower has two kinds of Dustin5. Most are paid: 5,000 Kill Coins a send,
5 items at most. A few are free, with no limit. **Every Dustin5 is free** makes
them all the free kind. Switched off, the paid ones stay paid at your price and
take your number of items.

## No waiting at Dustin5

**No waiting at Dustin5** (on): the menu opens straight away instead of up to
5 seconds later, and after a send there is no wait while Dustin5 and your
fighter play their animations.

## The Rewards Box

**Rewards Box: Storage Box and take everything** (on) adds three buttons to the
Rewards Box's list:

| Button       | What it does                                                         |
|--------------|----------------------------------------------------------------------|
| **Triangle** | Send the picked present to the Storage Box                           |
| **L1**       | Send everything that fits to the Storage Box                         |
| **R1**       | Take everything that fits, as taking each one would                  |

Each one asks Yes/No first, the way Delete does. Triangle on Kill Coins, a decal
or anything else that never goes in a bag takes it as usual, and the take asks
its own question.

- Weapons, armour, items, mushrooms and beasts go to the Storage Box. Kill
  Coins, SPLithium, Death Metals, decals and passes go where they always go.
- What does not fit (a full Storage Box, a full Death Bag, a full bank) stays in
  the Rewards Box.
- No result screen is shown for these: what is left in the box shows again.
- As with taking presents one at a time, the game saves what you took when you
  close the Rewards Box (or after 100).
- The Storage Box shows what arrived the next time you open it. (The game only
  refreshed it after you put something in, took something out or sorted; with
  this on, it refreshes each time it opens.)

The list's button guide shows all three after Delete: Store, Store All and
Take All. The game draws them for the pad or keyboard you are using, as it does
its own.

## What it needs

- **lid-betterdustin5.dll**, its plugin, comes with it from **Get mods**. It
  lets a paid Dustin5 take more than 5 items, and puts presents in the Storage
  Box.
- The game's file check off for `BrgGame.upk` and `SteamPCRelease-BrgUI.ini`
  (**Auto hash patch** does it as you save).

## What it changes

- `masters.db`: the Dustin5 kinds (`master_dustshooter`), or the paid price
  (`PRD_DUSTSHOOT`) and `master_const_int` `LID_DUSTIN_ITEMS` for the plugin.
- `BrgGame/Config/SteamPCRelease-BrgUI.ini`: `mCheckMax`, the Dustin5 menu's
  limit, while paid Dustin5s are on.
- `BrgGame.upk`: the no-waiting part (2 functions) and the Rewards Box part (4
  functions), as package patches that stack with the manager's other
  `BrgGame.upk` mods.

Unticking it and saving puts everything back.

## Built for game 5.0.5.0.0 - 1.92

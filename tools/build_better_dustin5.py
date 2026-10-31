"""Write the Better Dustin5 mod's patches for BrgGame.upk (.PackagePatch).

Two parts, each a switch in the mod:

- tfc/nodelay: no waiting at Dustin5.
  - BrgUIMenu_DustShooter.StartAnimDustUsing: returns at once. After a send
    the menu starts Dustin5's "using" animation and your fighter's, then
    waits for Dustin5 to be idle again; with neither started it is idle
    straight away.
  - BrgUIManager.StartDustShooterMenu: sets the menu's mEndPlayerLookDustin
    as it opens. The menu waits for it, or 5 seconds, before it shows.
- tfc/rewardbox: more ways out of the Rewards Box.
  - BrgUIMenu_PresentBox_ItemList.GetInputButton: Triangle, L1 and R1, which
    the list never used. Triangle asks for the picked present to go to the
    Storage Box (result 5), L1 for everything to go (6), R1 for everything to
    be taken as usual (7).
  - BrgUIMenu_PresentBox_ItemList.GetResult: says which present is picked for
    result 5 as well as for 2 (take) and 3 (delete).
  - BrgUIMenu_PresentBox.Tick: answers results 5, 6 and 7. A present for the
    Storage Box is queued like any other, with mOperate 2. Weapons, armour and
    items go to storage while it has room; Kill Coins, decals and the rest are
    taken as usual, where they always go. Taking everything skips what does
    not fit, as taking one would refuse it. No result screen is shown for
    these; what is left in the box shows again.
  - BrgUIMenu_PresentBox.NetReceiveItem: sends mOperate 2 as a "receive" of
    "@" plus the present's id. lid-betterdustin5.dll sees the "@" and has the
    game's server put that present in the Storage Box.
  - BrgUIMenu_PresentBox.Tick, state 7: Triangle, L1 and R1 ask first, with
    the delete's Yes/No and a question of their own: the game's "Storing
    item" for Triangle (COINLOCKER.TXT_LEAVE_MS), REWARDBOX.TXT_LIDALL_MS for
    L1 and REWARDBOX.TXT_LIDBAG_MS for R1 (both written by the mod's
    "rewardbox-ask" part). Yes does what the button is for. Kill Coins,
    decals and the rest skip Triangle's question: they go to the take, which
    asks its own.
  - BrgUIMenu_PresentBox.SetButtonGuide: the list's guide shows the three
    buttons after Delete - "Store" (the Storage Box's own word), "Store All"
    and "Take All". The game draws each one for the pad or keyboard in use.
  - BrgUIMenu_CoinLocker.TickASync: the Storage Box asks for its contents
    as it opens (an empty take-out), so what was sent there shows at once.

Every function is checked against the sizes it was written for, every changed
statement against its text, and each patch is applied to a copy of the
package to prove it lands where its export entry says. A .PackagePatch names
every object and name the new code uses, so the manager refuses it, rather
than forces it, on a package where any of them moved.

Reads the game's stock BrgGame.upk and never changes it. Needs a LiD DB Editor
checkout for its package reader:

    py -3 tools/build_better_dustin5.py --manager PATH/TO/LiD-DB-Editor --upk PATH/TO/BrgGame.upk
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

from upkpatch import Kit, o

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TFC = REPO / "mods" / "Better Dustin5" / "tfc"
PATCH_PATH = Path("Game") / "BrgGame" / "CookedPCConsole" / "BrgGame.upk.PackagePatch"
BOX = "BrgUIMenu_PresentBox"
LIST = "BrgUIMenu_PresentBox_ItemList"
OPERATE = f"{BOX}.BrgUIMenu_PresentBoxOperate"
ITEM = f"{LIST}.BrgUIMenu_PresentBoxItem"
KIND = f"{LIST}.BrgUIMenu_PresentBoxKind"
STORAGE = 2                     # the new mOperate: a receive into the Storage Box
MAX_QUEUED = 100                # the box sends its queue at this many, as the game does
DELETE_TEXT = b"REWARDBOX.TXT_DELETE_MS\x00"   # the delete's question, and ours, the same length
ALL_TEXT = b"REWARDBOX.TXT_LIDALL_MS\x00"      # (the mod's "rewardbox-ask" part writes LIDALL
BAG_TEXT = b"REWARDBOX.TXT_LIDBAG_MS\x00"      # and LIDBAG; "Storing item" is the game's own)
ONE_TEXT = b"COINLOCKER.TXT_LEAVE_MS\x00"
# the guide's entries: (EGamePadIcon, text); 3 is Y/Triangle, 4 L1, 5 R1
GUIDE = [(3, "COINLOCKER.TXT_LEAVE"), (4, "REWARDBOX.TXT_LIDALL"), (5, "REWARDBOX.TXT_LIDBAG")]
GUIDE_DELETE = (2, "MENU_GLOBAL.TXT_DELETE")   # the stock entry they are made from

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--manager", required=True, type=Path, help="a LiD DB Editor checkout")
parser.add_argument("--upk", required=True, type=Path, help="the game's stock BrgGame.upk")
parser.add_argument("--tfc", type=Path, default=TFC, help="where the tfc/<part> folders go")
parser.add_argument("--listing", type=Path, help="also write the changed code, disassembled, here")
args = parser.parse_args()

kit = Kit(args.manager, args.upk)
ref = kit.ref_of


# ------------------------------------------------------------ expression bits
def i32(v): return struct.pack("<i", v)
def intc(v): return b"\x25" if v == 0 else b"\x26" if v == 1 else b"\x2c" + bytes([v]) if v < 256 else b"\x1d" + i32(v)
def bytec(v): return b"\x24" + bytes([v])
def native(n, *a): return bytes([n]) + b"".join(a) + b"\x16"
def let(a, b): return b"\x0f" + a + b
def inst(path): return b"\x01" + o(ref(path))
def local(path): return b"\x00" + o(ref(path))
def b2i(e): return b"\x38\x3a" + e                     # byte -> int
def i2b(e): return b"\x38\x3d" + e                     # int -> byte
def member(prop, struct_path, e, lvalue=False):
    return b"\x35" + o(ref(prop)) + o(ref(struct_path)) + b"\x00" + (b"\x01" if lvalue else b"\x00") + e
def length(e): return b"\x36" + e
def element(index, array): return b"\x10" + index + array
def call(fn_path, *a): return b"\x1c" + o(ref(fn_path)) + b"".join(a) + b"\x16"
def ret_byte(v): return b"\x04" + bytec(v)
LT, GT, LE, GE, EQ, NE = 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B
ADD, SUB, AND, POSTINC, POSTDEC = 0x92, 0x93, 0x9C, 0xA5, 0xA6


def no_delay() -> list:
    anim = kit.fn("BrgUIMenu_DustShooter.StartAnimDustUsing", (9, 251, 175))
    anim.stmt(0x35, "return nothing")
    # "if (no target point or no Dustin5) return" -> return either way
    anim.poke(0x00, "jumpifnot 0x37 (N132(N114(I:BrgUIMenu_DustShooter.mTargetPoint, none)",
              b"\x07\x37\x00", b"\x07\x35\x00")

    start = kit.fn("BrgUIManager.StartDustShooterMenu", (7, 111, 79))
    opened = start.stmt_bytes(0x4D, "I:BrgUIManager.mDustShooterMenu.{skip=0xa,None,0}StartDustShooterMenu()")
    look = o(ref("BrgUIMenu_DustShooter.mEndPlayerLookDustin"))
    looked = (b"\x14\x19" + inst("BrgUIManager.mDustShooterMenu") + struct.pack("<H", 0x0A) + look + b"\x00"
              + b"\x2d\x01" + look + b"\x27")              # mDustShooterMenu.mEndPlayerLookDustin = true
    start.divert(0x4D, "I:BrgUIManager.mDustShooterMenu.", kit.asm()
                 .code(opened).code(looked).code(b"\x04\x0b"))
    return [anim, start]


def rewards_box() -> list:
    # -- the list: three more buttons ------------------------------------
    buttons = kit.fn(f"{LIST}.GetInputButton", (19, 262, 202))
    buttons.stmt(0xF8, "return 0b")
    edge = local(f"{LIST}.GetInputButton.Edge")
    pressed = lambda bit: native(NE, native(AND, edge, intc(bit)), intc(0))   # noqa: E731
    the_list = inst(f"{LIST}.mItemList")
    result = lambda v: let(inst(f"{LIST}.mResult"), bytec(v))               # noqa: E731
    done = b"\x1b" + struct.pack("<ii", kit.name_index("StartWait"), 0) + b"\x1e" + struct.pack("<f", 0.0) + intc(0) + b"\x16"
    buzz = call(f"{LIST}.PlaySound", bytec(3))
    picked = call(f"{LIST}.GetItemListIndexByCursorPos", inst(f"{LIST}.mCursor"))
    buttons.divert(0xF8, "return 0b", kit.asm()
        .jumpifnot("l1", pressed(128))                                      # Triangle: this one to storage
            .jumpifnot("buzz", native(LT, picked, length(the_list)))
            .code(result(5)).code(done).code(ret_byte(0))
        .label("l1").jumpifnot("r1", pressed(256))                          # L1: everything to storage
            .jumpifnot("buzz", native(GT, length(the_list), intc(0)))
            .code(result(6)).code(done).code(ret_byte(0))
        .label("r1").jumpifnot("none", pressed(512))                        # R1: take everything
            .jumpifnot("buzz", native(GT, length(the_list), intc(0)))
            .code(result(7)).code(done).code(ret_byte(0))
        .label("buzz").code(buzz).code(ret_byte(0))
        .label("none").code(ret_byte(0)))

    results = kit.fn(f"{LIST}.GetResult", (7, 130, 98))
    take_or_delete = results.stmt_bytes(0x26, "jumpifnot 0x6d (N132(N154(pcast0x3a(I:BrgUIMenu_PresentBox_ItemList.mResult), pcast0x3a(2b))")
    which = results.stmt_bytes(0x50, "O:BrgUIMenu_PresentBox_ItemList.GetResult.selectedListIndex = ")
    give = results.stmt_bytes(0x6D, "return I:BrgUIMenu_PresentBox_ItemList.mResult")
    results.divert(0x26, "jumpifnot 0x6d", kit.asm()
        .jumpifnot("five", take_or_delete[3:])                             # 2 or 3, as before
            .code(which).jump("give")
        .label("five").jumpifnot("give", native(EQ, b2i(inst(f"{LIST}.mResult")), b2i(bytec(5))))
            .code(which)
        .label("give").code(give))

    # -- the box: answer them --------------------------------------------
    tick = kit.fn(f"{BOX}.Tick", (295, 7366, 5266))
    got = tick.stmt_bytes(0x8DE, f"L:{BOX}.Tick.itemListResult = I:{BOX}.mPresentBoxItemList.")
    tick.stmt(0x910, f"switch<{BOX}.Tick.itemListResult,0>")
    WAIT = 0xA10
    tick.stmt(WAIT, "StartWait(0.0f, pcast0x3a(L:BrgUIMenu_PresentBox.Tick.tempState))")
    pick = tick.stmt_bytes(0x10BE, f"L:{BOX}.Tick.presentBoxItem = I:{BOX}.mItemList[I:{BOX}.mItemListSelectIndex]")
    # the delete's own statements, as the queue's: operate.mPresentId = ...,
    # mRewardOperateArray.AddItem(operate), mItemList.Remove(index, 1)
    name_it = tick.stmt_bytes(0x10FA, f"(L:{BOX}.Tick.operate).{OPERATE}.mPresentId[0,1] = ")
    queue = tick.stmt_bytes(0x1133, f"I:{BOX}.mRewardOperateArray.additem(L:{BOX}.Tick.operate)")
    unlist = tick.stmt_bytes(0x1149, f"I:{BOX}.mItemList.remove(I:{BOX}.mItemListSelectIndex,1)")
    add_up = tick.stmt_bytes(0x1370, f"F:{BOX}.PopulateItem(L:{BOX}.Tick.presentBoxItem)")
    tick.stmt(0x13C9, f"(L:{BOX}.Tick.operate).{OPERATE}.mOperate[0,1] = 0b")

    state = local(f"{BOX}.Tick.tempState")
    answer = local(f"{BOX}.Tick.itemListResult")
    room = local(f"{BOX}.Tick.netPresentBoxStatus")     # free here: storage slots left
    item = local(f"{BOX}.Tick.presentBoxItem")
    operate = local(f"{BOX}.Tick.operate")
    index = inst(f"{BOX}.mItemListSelectIndex")
    # While a question is up, the picked index says whose it is: -1 L1's,
    # -2 R1's, and ONE - index Triangle's for that present (0 and up stay
    # the delete's). No does not read it; the list sets it again.
    ASK_ALL = b"\x1d" + i32(-1)
    ASK_BAG = b"\x1d" + i32(-2)
    ONE = b"\x1d" + i32(-10)
    items = inst(f"{BOX}.mItemList")
    queued = inst(f"{BOX}.mRewardOperateArray")
    to = lambda v: let(state, bytec(v))                                     # noqa: E731
    operation = lambda v: let(member(f"{OPERATE}.mOperate", OPERATE, operate, lvalue=True), bytec(v))  # noqa: E731
    kind = member(f"{ITEM}.mKind", ITEM, item)
    in_the_bag = native(EQ, b2i(call(f"{BOX}.GetResultType", member(f"{KIND}.mType", KIND, kind))), b2i(bytec(0)))
    no_room = call(f"{BOX}.CheckNoCapacity", kind, member(f"{ITEM}.mNum", ITEM, item))
    user_data = b"\x19" + inst("BrgUIBase.mUIManager") + struct.pack("<H", 9) + o(ref("BrgUIManager.mUserData")) + b"\x00" + inst("BrgUIManager.mUserData")
    space_call = b"\x1b" + struct.pack("<ii", kit.name_index("GetCoinLockerSpaceSlotCount"), 0) + b"\x16"
    space = (b"\x19" + user_data + struct.pack("<H", kit.mem_len(space_call))
             + o(ref("BrgUserData.GetCoinLockerSpaceSlotCount.ReturnValue")) + b"\x00" + space_call)

    def then_next(a, tag):
        """tempState for what comes next: the box is empty, the queue is full, or the list again."""
        return (a.jumpifnot(f"{tag}-a", native(LE, length(items), intc(0))).code(to(3)).jump(WAIT)
                 .label(f"{tag}-a").jumpifnot(f"{tag}-b", native(GE, length(queued), intc(MAX_QUEUED)))
                 .code(to(10)).jump(WAIT)
                 .label(f"{tag}-b").code(to(5)).jump(WAIT))

    def count_room(a, tag):
        """room = the Storage Box's free slots, less the presents already queued for it."""
        at = b2i(state)
        return (a.code(let(room, space)).code(to(0))
                 .label(f"{tag}-loop").jumpifnot(f"{tag}-done", native(LT, at, length(queued)))
                 .jumpifnot(f"{tag}-skip", native(EQ, b2i(member(f"{OPERATE}.mOperate", OPERATE, element(at, queued))),
                                                  b2i(bytec(STORAGE))))
                 .code(native(POSTDEC, room))
                 .label(f"{tag}-skip").code(let(state, i2b(native(ADD, at, intc(1))))).jump(f"{tag}-loop")
                 .label(f"{tag}-done"))

    def take_all(a, tag, storage):
        a = count_room(a, tag) if storage else a
        a = (a.code(let(index, intc(0)))
              .label(f"{tag}-each").jumpifnot(f"{tag}-end", native(LT, index, length(items)))
              .jumpifnot(f"{tag}-end", native(LT, length(queued), intc(MAX_QUEUED)))
              .code(pick))
        if storage:
            a = (a.jumpifnot(f"{tag}-take", in_the_bag)
                  .jumpifnot(f"{tag}-next", native(GT, room, intc(0)))
                  .code(operation(STORAGE)).code(name_it).code(queue).code(unlist).code(native(POSTDEC, room))
                  .jump(f"{tag}-each"))
        a = (a.label(f"{tag}-take").jumpifnot(f"{tag}-fits", no_room).jump(f"{tag}-next")
              .label(f"{tag}-fits").code(add_up).code(operation(0)).code(name_it).code(queue).code(unlist)
              .jump(f"{tag}-each")
              .label(f"{tag}-next").code(native(POSTINC, index)).jump(f"{tag}-each")
              .label(f"{tag}-end").code(let(index, intc(0))))
        return then_next(a, f"{tag}-then")

    def one_to_storage(a, tag):
        """The picked present (a bag item) to the Storage Box, if it has room."""
        a = count_room(a.code(pick), tag)
        a = (a.jumpifnot(f"{tag}-full", native(GT, room, intc(0)))
              .code(operation(STORAGE)).code(name_it).code(queue).code(unlist))
        a = then_next(a, f"{tag}-then")
        return a.label(f"{tag}-full").code(to(5)).jump(WAIT)

    a = (kit.asm().code(got)
         .jumpifnot("not5", native(EQ, b2i(answer), b2i(bytec(5)))))
    # Triangle: ask, then the picked present to the Storage Box. Anything
    # that does not go in a bag (Kill Coins, decals...) is taken as usual
    # instead, and the take asks its own question.
    a = (a.code(pick)
          .jumpifnot("one-ask", native(NE, b2i(call(f"{BOX}.GetResultType", member(f"{KIND}.mType", KIND, kind))),
                                       b2i(bytec(0))))
          .jumpifnot("one-fits", no_room).code(to(4)).jump(WAIT)
          .label("one-fits").code(to(6)).jump(WAIT)
          .label("one-ask").code(let(index, native(SUB, ONE, index))).code(to(7)).jump(WAIT))
    # L1 and R1: ask first, with the delete's Yes/No (state 7)
    a = a.label("not5").jumpifnot("not6", native(EQ, b2i(answer), b2i(bytec(6))))
    a = a.code(let(index, ASK_ALL)).code(to(7)).jump(WAIT)
    a = a.label("not6").jumpifnot("back", native(EQ, b2i(answer), b2i(bytec(7))))
    a = a.code(let(index, ASK_BAG)).code(to(7)).jump(WAIT)
    a = a.label("back").jump(0x910)
    tick.divert(0x8DE, f"L:{BOX}.Tick.itemListResult = ", a)

    # state 7: our questions, or the game's for a delete
    asking = f"I:BrgUIBase.mUIManager.{{skip=0x9,BrgUIManager.mSystemWindow,0}}I:BrgUIManager.mSystemWindow."
    ask_delete = tick.stmt_bytes(0xF01, asking)
    if ask_delete.count(DELETE_TEXT) != 1:
        raise SystemExit("PresentBox.Tick: the delete question is not the one this was written for")
    is_all = native(EQ, index, ASK_ALL)
    is_bag = native(EQ, index, ASK_BAG)
    is_one = native(LE, index, ONE)
    tick.divert(0xF01, asking, kit.asm()
        .jumpifnot("q-bag", is_all).code(ask_delete.replace(DELETE_TEXT, ALL_TEXT)).jump(0xF68)
        .label("q-bag").jumpifnot("q-one", is_bag).code(ask_delete.replace(DELETE_TEXT, BAG_TEXT)).jump(0xF68)
        .label("q-one").jumpifnot("q-delete", is_one).code(ask_delete.replace(DELETE_TEXT, ONE_TEXT)).jump(0xF68)
        .label("q-delete").code(ask_delete).jump(0xF68))
    # Yes: what the button asked for, or the delete as before (the Yes/No
    # test is replaced: the delete's own first statement is too short)
    answered = tick.stmt_bytes(0x1049, "jumpifnot 0x11a9 (")
    a = kit.asm().jumpifnot(0x11A9, answered[3:]).jumpifnot("y-bag", is_all)
    a = take_all(a, "store", storage=True)
    a = a.label("y-bag").jumpifnot("y-one", is_bag)
    a = take_all(a, "bag", storage=False)
    a = a.label("y-one").jumpifnot(0x10BE, is_one).code(let(index, native(SUB, ONE, index)))
    a = one_to_storage(a, "one")
    tick.divert(0x1049, "jumpifnot 0x11a9 (", a)

    # -- what is sent: "@" in front of a present for storage ---------------
    send = kit.fn(f"{BOX}.NetReceiveItem", (15, 430, 282))
    pid = send.stmt_bytes(0xDC, f"(L:{BOX}.NetReceiveItem.operatePresentHistory).BrgGameBase.BrgNetworkDeclStruct."
                                "BrgDbOperatePresentHistory.mPid[0,1] = ")
    receive = send.stmt_bytes(0x8E, f"(L:{BOX}.NetReceiveItem.operatePresentHistory).BrgGameBase.BrgNetworkDeclStruct."
                                    "BrgDbOperatePresentHistory.mType[0,1] = 'receive'")
    send.stmt(0x115, f"(L:{BOX}.NetReceiveItem.operatePresentParam).")
    sent = local(f"{BOX}.NetReceiveItem.operate")
    its_id = member(f"{OPERATE}.mPresentId", OPERATE, sent)
    if not pid.endswith(its_id):
        raise SystemExit("NetReceiveItem: the id statement is not the one this was written for")
    marked = pid[:-len(its_id)] + native(0x70, b"\x1f@\x00", its_id)        # "@" $ operate.mPresentId
    send.divert(0xDC, f"(L:{BOX}.NetReceiveItem.operatePresentHistory).", kit.asm()
        .jumpifnot("plain", native(EQ, b2i(member(f"{OPERATE}.mOperate", OPERATE, sent)), b2i(bytec(STORAGE))))
            .code(receive).code(marked).jump(0x115)
        .label("plain").code(pid).jump(0x115))

    # -- the Storage Box: shown as it is now ------------------------------
    # The game keeps its own copy of the Storage Box, rebuilt only from a
    # Storage Box reply (put in, take out, sort). The Rewards Box's reply has
    # none, so what Triangle and L1 sent would not show. As it opens, the menu
    # now takes out nothing - state 7 with nothing picked, an empty "drawcl"
    # whose reply holds the whole Storage Box - and goes on to its main menu
    # from there, as after any take-out.
    locker = kit.fn("BrgUIMenu_CoinLocker.TickASync", (257, 7294, 5302))
    locker.poke(0x2A4, "StartWait(0.0f, 3)", intc(3), intc(7))         # opened: -> take out, then 3

    # -- the list's button guide: the three buttons -----------------------
    # Made from the Delete entry's own three statements (icon, text, add),
    # which run only for the list's guide.
    guide = kit.fn(f"{BOX}.SetButtonGuide", (38, 992, 696))
    info = f"(L:{BOX}.SetButtonGuide.lButtonInfo).BrgUIMenuPart_ButtonGuide.BrgUIButtonGuideUnitBaseInfo."
    icon_of = guide.stmt_bytes(0x311, info + f"mIcon[0,1] = {GUIDE_DELETE[0]}b")
    name_of = guide.stmt_bytes(0x330, info + "mName[0,1] = ")
    add = guide.stmt_bytes(0x38A, f"L:{BOX}.SetButtonGuide.lButtonInfoArray.additem(")
    old_text = b"\x1f" + GUIDE_DELETE[1].encode("latin-1") + b"\x00"
    returns = o(ref("BrgGameBase.BrgUIManagerBase.GetLocalizeTextST.ReturnValue"))
    if not icon_of.endswith(bytec(GUIDE_DELETE[0])) or name_of.count(old_text) != 1 or name_of.count(returns) != 1:
        raise SystemExit("PresentBox.SetButtonGuide: the Delete entry is not the one this was written for")
    at = name_of.index(returns) - 2                  # the call's size, just before its result
    skip = struct.unpack_from("<H", name_of, at)[0]
    entries = kit.asm().code(add)
    for icon, text in GUIDE:
        new_text = b"\x1f" + text.encode("latin-1") + b"\x00"
        named = name_of.replace(old_text, new_text)
        named = named[:at] + struct.pack("<H", skip + len(new_text) - len(old_text)) + named[at + 2:]
        entries = entries.code(icon_of[:-2] + bytec(icon)).code(named).code(add)
    guide.divert(0x38A, f"L:{BOX}.SetButtonGuide.lButtonInfoArray.additem(", entries.jump(0x3A0))

    return [buttons, results, tick, send, locker, guide]


PARTS = {"nodelay": no_delay, "rewardbox": rewards_box}
listing = []
for name, make in PARTS.items():
    print(f"--- {name}")
    functions = make()
    kit.write_patch(functions, args.tfc / name / PATCH_PATH)
    listing.append(f"=== {name}\n" + kit.listing(functions))
if args.listing:
    args.listing.write_text("\n".join(listing), encoding="utf-8")

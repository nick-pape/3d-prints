# clip-box

A hinged box with four sealed sections for hair clips, with a sliding bolt you have to turn to lock it. Parametric
(build123d), sized for a Prusa MK4 bed, printed in PETG with a 0.6 mm nozzle.

- **Sealed sections:** the lid carries a ring for each section that drops 4 mm into it. With the lid shut every
  section is a closed cup, so a shake or a drop doesn't mix the clips.
- **Hinges:** two, at the back corners. Each is base knuckle, lid knuckle, base knuckle on an M3 × 30 bolt with a
  nyloc nut (the head and nut sit in pockets). Stops hold the lid open at about 102°.
- **Lock:** a round bolt slides up from a housing on the front into a keeper on the lid. A knob on an M3 × 16 screw
  rides in a stretched-Z slot: turn it sideways into the top notch to lock, or the bottom notch to park it open.
  A small bump at each notch makes it click, so it takes a deliberate twist.

## Files (`out/`)

| File | What |
|---|---|
| `clip_box_base.3mf` | Base, ready to slice (MK4, 0.6 HF, Prusament PETG, 0.40 mm). About 290 g, 5 h 10 min. |
| `clip_box_lid.3mf` | Lid (printed upside down), bolt and knob. About 163 g, 2 h 40 min. |
| `testfit.3mf` | Print this first: one hinge, the lock, bolt and knob. About 30 g, 46 min. |
| `base.stl`, `lid.stl`, `bolt.stl`, `knob.stl` | The parts in print orientation. |

## Hardware

- 2 × M3 × 30 socket head screw + 2 × M3 nyloc nut (hinges)
- 1 × M3 × 16 screw (knob; it threads into the bolt's pilot hole)

## Assembly

1. Push a nyloc into the hex pocket on each hinge. Line up the knuckles and push the M3 × 30 through from the
   head side, then tighten until the lid swings freely without flopping sideways.
2. With the lid open, drop the bolt (chamfered end up) into the housing, flat facing out through the slot.
3. Screw the knob onto the bolt through the slot with the M3 × 16.

## Build

    uv run python box.py        # out/base.stl, lid.stl, bolt.stl, knob.stl
    uv run python check.py      # swings the lid through its travel and checks the lock parts for collisions
    uv run python render.py     # preview renders
    uv run python testfit.py    # test-fit pieces
    uv run python tools/make_3mf.py out/clip_box_base.3mf tools/petg_hf06.ini out/base.stl

Main knobs (`Params` in `box.py`): `W`, `D`, `Hb`, `Hl`, `wall`, `div`, `seal_c` (lid ring clearance),
`knuckle_c`, `open_deg`, `bolt_c`, `detent`, `turn_deg`.

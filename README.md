# 3d-prints

Parametric 3D-printable designs, generated in code (build123d). Each folder is its own project with its own
`pyproject.toml`; `cd` into it and use `uv run` as its README says.

| Project | What | |
|---|---|---|
| [`powerbank-station/`](powerbank-station/) | Desk charging station for power banks, with a cable box. | [Generator](https://nick-pape.github.io/3d-prints/powerbank-station/) · [Printables](https://www.printables.com/model/1928299) |
| [`clip-box/`](clip-box/) | Hinged box with four sealed sections and a turn-to-lock bolt, for hair clips. | |

Slatwall shelves and mounts live in their own repo,
[slatwall-accessories](https://github.com/nick-pape/slatwall-accessories).

GitHub Pages (`pages/` landing + the powerbank generator) deploys from `.github/workflows/pages.yml`. In a Coder
workspace, `.coder/start.sh` serves the same layout on the dev port.

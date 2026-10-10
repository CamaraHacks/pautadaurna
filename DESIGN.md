# Design system — Mapa da Abstenção

A small, dependency-free system built for one job: helping organizers find where abstainers are and how to reach them.
Visual identity: white paper with **red** (accent, abstention numbers) and **yellow** (highlighter, source labels),
a voting-machine (urna) illustration in the hero, and buttons shaped like urna keys: the black number key marks the
active tab, the orange **CORRIGE** key clears filters, the white **BRANCO** key copies text. Single light theme by choice.
The choropleth runs yellow → red. Candidates never get a color. Data-viz rules follow IBM Carbon's data patterns.

## Tokens (`site/template.html`, `:root`)

| Role | Value | Use |
|---|---|---|
| `--ground` / `--panel` | `#fdfcf9` / `#ffffff` | paper background / cards, charts, inputs |
| `--ink` / `--ink-2` / `--ink-3` | `#191714` / `#4f4a42` / `#857e72` | text hierarchy |
| `--rule` | `#e6e1d6` | borders, grid lines |
| `--accent` / `--accent-ink` | `#c81e2b` / `#a3121e` | red: headline numbers, focus ring, "acima da média" |
| `--yellow` / `--yellow-soft` | `#f5c400` / `#fff1b3` | highlighter marks, source labels, app bar rule |
| `--corrige` / `--confirma` | `#e2632b` / `#1f8a4c` | urna keys: clear filters / "Copiado" confirmation |
| `--s-2026` / `--s-2022` | red / warm grey | current vs. reference series |
| `--seq-0…6` | yellow → dark red | choropleth (sequential) |
| `--div-neg/mid/pos` | steel blue / paper grey / red | change since 2022 (diverging) |
| `--g1…g5` | validated categorical slots 1–5 | the five abstainer groups, fixed order, never cycled |

Candidates are never given a color. Political lean is drawn in neutral inks.

Type: **Archivo** (condensed, display), **Source Serif 4** (reading), **IBM Plex Mono** (numbers, labels, controls).

## Components

| Component | Behavior |
|---|---|
| **AppBar + Tabs** | Sticky. Four views: Panorama, Onde agir, Kit de redes, Método. Active tab is filled ink. |
| **FilterBar** | Cidade (searchable list), Estado, Grupo, Limpar. Global: applies to every tab, stored in the URL (`#/explorar?c=3550308&g=jovens`). |
| **Scope chips** | "Você está vendo: …" with one removable chip per active filter. Tells the user what the numbers refer to. |
| **Steps** | The only numbered element; it is a real sequence (choose → see → take the kit). |
| **Visor (KPI tiles)** | Three numbers max, mono, one in accent. |
| **Compare bars** | Two quantities on one scale (abstainers vs. vote margin; city vs. Brasil share). |
| **Badge** | State in shape and word, not color alone: ▲ acima da média, ▼ abaixo, ● na média. |
| **DataTable** | Sortable headers (`aria-sort`), city names are buttons that open the city, "Mostrar mais". |
| **Group chooser / group cards** | Pressed state uses an underline, not only color. |
| **Chip** | Topic (plain) or keyword (`#`, with "Trends ↗" link). |
| **Copy button + Toast** | Every message and keyword set is one click to copy; a toast confirms "Copiado". |
| **Tag** | `estimativa`, `hipótese`, `inferência`: marks anything that is our reading, not measured data. |
| **Details** | Sensitive or secondary content (political lean) stays collapsed by default. |

## Rules

- Summary before detail; every view opens in a useful state (Brasil ranking, group overview).
- One accent; semantic state is shape + text.
- All charts redraw from tokens on theme change; text never takes a series color.
- Single self-contained HTML (works offline, on GitHub Pages and as an artifact); `[hidden]` is enforced in our own CSS.

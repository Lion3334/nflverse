# Archived design explorations

The active product is [the live site](https://lion3334.github.io/nflverse/), built from `web/index.template.html` into `docs/index.html`. Superseded design previews were removed from the working tree to keep source files and deployment artifacts easy to identify. Their files remain available in Git history; no history was rewritten.

Last complete revision before cleanup: [`9d150cc`](https://github.com/Lion3334/nflverse/tree/9d150cc).

| Archived material | Historical files |
| --- | --- |
| A/B/C matchup design studies, compact table mockups, templates, generators, and screenshots | [designs/](https://github.com/Lion3334/nflverse/tree/9d150cc/designs) |
| Early dashboard prototype and downloadable ZIP; illustrative data, not current ratings | [prototypes/](https://github.com/Lion3334/nflverse/tree/9d150cc/prototypes) |
| Superseded matchup and leaderboard screenshots | [docs/](https://github.com/Lion3334/nflverse/tree/9d150cc/docs) |

To inspect an old file without changing the working tree:

```sh
git show 9d150cc:designs/README.md
```

Keep future temporary screenshots and mock build outputs outside `docs/` (for example, `/tmp`). `docs/` is the production Pages artifact directory. Historical EPA snapshots under `reports/` are application data and must remain: the live site uses them to avoid hindsight in earlier matchups.

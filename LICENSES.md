# Third-party licences

This project’s own licence is the MIT licence in `LICENSE`.

The compiled files under `assets/vendor/` are unchanged upstream distributions. Preserve those notices if you redistribute them.

## Chart.js 4.5.1

- Licence: MIT
- Copyright: 2014–2024 Chart.js Contributors
- Files: `assets/vendor/chart.js/`
- Upstream: <https://github.com/chartjs/Chart.js>
- Notice: `assets/vendor/chart.js/LICENSE.md`

Chart.js is loaded only on the dashboard. The rest of the template does not depend on it.

## Basecoat 1.0.2

- Licence: MIT
- Files: `app/ui/static/vendor/basecoat/` and `app/ui/templates/basecoat/`
- Package: `basecoat-css@1.0.2`
- Upstream: <https://github.com/hunvreus/basecoat>
- Docs: <https://basecoatui.com/introduction/>
- Notice: `app/ui/static/vendor/basecoat/LICENSE.md`

The CSS file is the standalone Vega bundle. It embeds Tailwind CSS 4, which is also MIT. Icons on the pages are inline SVGs, not a vendored icon package.


# Third-party licences

This project’s own licence is the MIT licence in `LICENSE`.

The compiled files under `assets/vendor/` are unchanged upstream distributions. Preserve those notices if you redistribute them.

## Bootstrap 5.3.8

- Licence: MIT
- Copyright: 2011–2025 The Bootstrap Authors
- Files: `assets/vendor/bootstrap/`
- Upstream: <https://github.com/twbs/bootstrap>
- Notice: `assets/vendor/bootstrap/LICENSE`

`assets/vendor/bootstrap/bootstrap-logo.svg` is the official Bootstrap mark from the examples package, used on the sign-in page.

## Bootstrap Icons 1.13.1

- Licence: MIT
- Copyright: 2019–2024 The Bootstrap Authors
- Files: `assets/vendor/bootstrap-icons/`
- Upstream: <https://github.com/twbs/icons>
- Notice: `assets/vendor/bootstrap-icons/LICENSE.md`

## Chart.js 4.5.1

- Licence: MIT
- Copyright: 2014–2024 Chart.js Contributors
- Files: `assets/vendor/chart.js/`
- Upstream: <https://github.com/chartjs/Chart.js>
- Notice: `assets/vendor/chart.js/LICENSE.md`

Chart.js is loaded only on the dashboard. The rest of the template does not depend on it.

## Colour mode script

`assets/js/admin.js` adapts Bootstrap’s documentation colour-mode snippet:

- Source: <https://getbootstrap.com/docs/5.3/customize/color-modes/>
- Copyright: 2011–2025 The Bootstrap Authors
- Licence: Creative Commons Attribution 3.0 Unported

## Basecoat 1.0.2

- Licence: MIT
- Files: `app/ui/static/vendor/basecoat/` and `app/ui/templates/basecoat/`
- Package: `basecoat-css@1.0.2`
- Upstream: <https://github.com/hunvreus/basecoat>
- Docs: <https://basecoatui.com/introduction/>
- Notice: `app/ui/static/vendor/basecoat/LICENSE.md`

The CSS file is the standalone Vega bundle. It embeds Tailwind CSS 4, which is also MIT. Icons are not part of Basecoat; this app still vendors Bootstrap Icons.


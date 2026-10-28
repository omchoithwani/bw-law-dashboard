# BW Law dashboard

Month-to-date collections and inbound calls, embedded in a HubSpot reporting dashboard via External content.

Live page: https://omchoithwani.github.io/bw-law-dashboard/

## Daily update

1. Export the four MyCase payment reports (Crim, PI, EP, Civil) and the phone analytics table as CSV.
2. Put them in one folder (outside this repo; CSVs are git-ignored because they contain client names).
3. `python3 build/build.py <csv folder> index.html`
4. Commit and push `index.html`.

The page carries aggregates only: no client or case names.

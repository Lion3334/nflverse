# Team logo assets

These are the original PNG bytes from `logo_list` in `R/sysdata.rda` in [nflverse/nflplotR](https://github.com/nflverse/nflplotR/tree/7872fba39df46f569fda13a608acec1c6231991d). The exact source commit and individual SHA-256 checksums are recorded in `sources.json`. No image modifications were made. `LA.png` corresponds to the Los Angeles Rams, following the source data's team abbreviation.

nflplotR's `data-raw/build_logo_list.R` identifies the upstream team images as ESPN CDN logos, with the Jets logo from NFL.com. Team logos and trademarks belong to their respective owners; inclusion identifies teams for this personal, non-commercial research tool and does not imply affiliation or endorsement.

`build_site.py` verifies the checksums and embeds the PNG files as data URLs in the HTML. The deployed or downloaded page makes no image requests to outside services. Rebuilding needs no additional Python packages for logos.

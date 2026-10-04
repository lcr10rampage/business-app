# Bringing the WordPress posts into Webflow

Everything from thetaoblog.com is saved here, so the import does not need WordPress later
(unless you choose to pull images from it). 38 posts are on the new site so far: the 20
newest, plus 2 from each year 2017-2025 as samples (listed in `state.json`).

## What is here

| File | What it is |
|---|---|
| `writings-all.json` | All 1,735 posts, cleaned for Webflow. One record per post. |
| `report.md` | Counts by year, duplicates, and everything the cleanup changed. |
| `redirects.csv` | Old WordPress address to new address, for the day the domain moves. |
| `../wordpress/` | The raw WordPress data, untouched (the source of truth). |
| `../../assets/wp-import/` | Every image (2,043 of 2,046; 3 were already broken on WordPress). |
| `../../tools/import_writings.py` | The importer. |
| `../../tools/wp_export.py` | Rebuilds this folder from WordPress (only needed if Andrew posts more there). |

## What is in the posts

- 1,735 posts, Aug 2017 to Jun 2026. Most are short: an image (often a quote card) and a caption.
  246 are 300+ words ("Essay"); 1,489 are shorter ("Reflection").
- 118 are exact copies of an earlier post (same text, same image).
- 128 more repeat an earlier post's words with a new image or title.
- 255 end with a "TheTaoBlog.com" line; 10 have hashtag-only lines.
- 134 had an Amazon Kindle preview of Andrew's book. Webflow can't embed those, so each
  became a "Read a free sample on Kindle" link. YouTube videos are kept as videos.
- No image has alt text in WordPress. Images import as decorative until someone describes them.

## Questions for Andrew (each answer is one option on the command)

| Question | Option |
|---|---|
| Which posts? All, or from a date? | `--since 2023-01-01` (and/or `--until ...`) |
| Only the long pieces, or the short image posts too? | `--kind Essay` or `--kind Reflection` |
| Leave out exact copies? | `--skip-duplicates` |
| Leave out re-posts of the same words with a new image? | `--skip-repeats` |
| Drop the "TheTaoBlog.com" lines? | `--strip-signature` |
| Drop hashtag lines? | `--strip-hashtags` |
| A hand-picked list? | `--only list.txt` (slugs or old URLs, one per line) |

## Before running it

1. **Plan.** Webflow's free plan holds 50 CMS items; the site has 45 now. Any more posts
   need the CMS plan (2,000 items). That is Chet's call.
2. **Blog page lists.** The Blog page reads posts from Collection Lists of 100 (Webflow's
   cap per list). One list exists today (newest 100). For each further 100 posts, add one
   more list with the same card and Offset 100, 200, ... (up to 20 lists = 2,000 posts).
   Ask Lena; it is a few minutes per list. Topics travel in the three Topic dropdowns.
3. **Token.** In Webflow: Site settings > Apps & integrations > API access > Generate
   token, with CMS and Assets read + write. Keep it out of files and chat.

## Putting in all the posts (checked 2026-10-04)

WordPress reports 1,735 posts and `writings-all.json` holds all 1,735, matched one for one
by WordPress ID. To bring in everything (except exact copies, if Andrew agrees):

```bash
python3 tools/import_writings.py --skip-duplicates --strip-signature        # look first
python3 tools/import_writings.py --skip-duplicates --strip-signature --go   # do it
```

- **Posts:** 1,617 go in (1,735 less 118 exact copies). Add `--skip-repeats` to leave out
  the 128 re-posts too (1,489 go in). The 38 already on the site are skipped automatically.
- **Blog page lists:** 1,617 posts need 17 Collection Lists (offsets 0-1,600); 1,489 need 15.
- **Time:** about 65 minutes for 1,617 posts.
- **Pictures:** every picture that still loads on WordPress is saved (2,043). Known gaps:
  - 3 were already broken on WordPress, so they can't be brought over.
  - 27 posts never had a picture.
  - 133 have pictures only inside the post and no tile picture, so they show a plain tile
    on the Blog page. Chet chose to leave these as they are (2026-10-04).
- **Backup:** the posts and code are in git (business-app, branch `tao-blog-webflow`).
  The pictures in `assets/wp-import/` (489 MB) are left out of git and exist only on the
  agent-runtime VM.

## Running it

```bash
cd workspace/business-app/the-tao-blog-webflow
export WEBFLOW_TOKEN=paste-the-token-here

# 1. Look first. This sends nothing; it shows what would go in and checks every post.
python3 tools/import_writings.py --since 2023-01-01 --skip-duplicates --strip-signature

# 2. Same command plus --go to do it.
python3 tools/import_writings.py --since 2023-01-01 --skip-duplicates --strip-signature --go

# 3. Publish the site in Webflow. Imported posts are staged until then (or add --live).
```

- Safe to run again: posts already in the collection are skipped, and progress is saved
  in `state.json`. If it stops partway (plan limit, network), fix the cause and rerun.
- If WordPress has been switched off, add `--images local` to upload the saved copies.
- It takes about a minute per 25 posts (Webflow allows 60 requests a minute).

## Undoing it

`state.json` lists every Webflow item the importer created. In the Webflow CMS you can
select and delete them. Ask Lena to script it if there are many.

## Tested

`python3 tests/test_importer.py` runs the importer end to end against a fake Webflow on
this machine. It covers the dry run, batching, a rate-limit retry, rerun safety, local
image upload, live mode and the cleanup options. Webflow's real handling of image URLs and
YouTube embeds was checked with one draft item on the real site (since deleted). A real
import has not been run.

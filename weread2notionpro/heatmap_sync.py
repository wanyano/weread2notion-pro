"""CLI to export and optionally publish a Notion Pro daily heatmap.

Only the explicit --update-embed command touches the Notion embed.
The export step reads the 日 database and writes a local SVG file.
"""
import argparse
import os
from pathlib import Path
from datetime import datetime
from weread2notionpro.heatmap_renderer import TZ, days_from_notion_rows, render_svg

def helper():
    os.environ["NOTION_READ_ONLY"]="true"
    from weread2notionpro.notion_helper import NotionHelper
    return NotionHelper()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--year",type=int,default=datetime.now(TZ).year)
    parser.add_argument("--update-embed",action="store_true")
    args=parser.parse_args()
    if not 2000 <= args.year <= datetime.now(TZ).year:
        raise ValueError("Invalid heatmap year")
    notion=helper()
    if not notion.day_database_id:
        raise ValueError("Notion Pro 日 database not found")
    if args.update_embed:
        if not notion.heatmap_block_id:
            raise ValueError("No existing heatmap embed block found on NOTION_PAGE; existing page unchanged")
        owner=os.environ.get("GITHUB_REPOSITORY")
        sha=os.environ.get("HEATMAP_COMMIT")
        if not owner or not sha or len(sha)<7:
            raise ValueError("Missing GitHub repository/committed revision for heatmap URL")
        # Pin by commit SHA so the image is immutable and avoids GitHub raw caching.
        raw=f"https://raw.githubusercontent.com/{owner}/{sha}/OUT_FOLDER/weread_{args.year}.svg"
        url=f"https://heatmap.malinkang.com/?image={raw}"
        notion.update_heatmap(block_id=notion.heatmap_block_id,url=url)
        print(f"HEATMAP_EMBED_UPDATED: year={args.year} revision={sha[:12]}")
        return
    rows=notion.query_all(database_id=notion.day_database_id)
    days,existing,duplicates=days_from_notion_rows(rows,args.year)
    nonzero=sum(1 for sec in days.values() if sec>0)
    svg=render_svg(args.year,days)
    path=Path("OUT_FOLDER")/f"weread_{args.year}.svg"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(svg,encoding="utf-8")
    print(f"HEATMAP_AUDIT: year={args.year} notion_rows={existing} recorded_days={len(days)} positive_days={nonzero} duplicates={duplicates}")
    print(f"HEATMAP_FILE: {path.as_posix()}")
    print("HEATMAP_EXPORT_ONLY: no Notion pages or embeds modified")

if __name__=="__main__":
    main()

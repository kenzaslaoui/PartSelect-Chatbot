"""Test script to debug product description and video scraping."""

from bs4 import BeautifulSoup

# Read the HTML file
with open('Crisper_Drawer.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'lxml')

print("=" * 80)
print("TESTING PRODUCT DESCRIPTION SCRAPING")
print("=" * 80)

# --- Product description ---
desc_section = soup.find('div', id='ProductDescription')
print(f"\n1. Found ProductDescription section: {desc_section is not None}")

if desc_section:
    # Find the itemprop="description" div
    desc_div = desc_section.find('div', {'itemprop': 'description'})
    print(f"2. Found itemprop='description' div: {desc_div is not None}")

    if desc_div:
        description = desc_div.get_text(strip=True)
        print(f"3. Extracted description: {description[:100]}...")
    else:
        print("   ERROR: Could not find itemprop='description' div")
        print(f"   desc_section contents: {desc_section.prettify()[:500]}")
else:
    print("   ERROR: Could not find ProductDescription section")

print("\n" + "=" * 80)
print("TESTING VIDEO SCRAPING")
print("=" * 80)

# --- Part videos ---
video_section = soup.find('div', id='PartVideos')
print(f"\n1. Found PartVideos section: {video_section is not None}")

if video_section:
    # Find all video containers
    video_containers = video_section.find_all('div', class_='yt-video')
    print(f"2. Found {len(video_containers)} video containers")

    videos = []
    for i, vid_container in enumerate(video_containers):
        yt_id = vid_container.get('data-yt-init')
        print(f"\n   Video {i+1}:")
        print(f"   - YouTube ID: {yt_id}")

        if yt_id:
            # Get video title from the following h4 or p tag
            title_tag = vid_container.find_next('h4')
            if not title_tag:
                title_tag = vid_container.find_next('p')

            video_title = title_tag.get_text(strip=True) if title_tag else 'Part Installation Video'
            print(f"   - Title: {video_title}")

            videos.append({
                'title': video_title,
                'youtube_id': yt_id,
                'url': f'https://www.youtube.com/watch?v={yt_id}'
            })

    print(f"\n3. Total videos extracted: {len(videos)}")
    if videos:
        print("\nExtracted videos:")
        for v in videos:
            print(f"   - {v['title']} ({v['youtube_id']})")
else:
    print("   ERROR: Could not find PartVideos section")

print("\n" + "=" * 80)

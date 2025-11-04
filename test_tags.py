from src.services.youtube_api import YouTubeAPIClient

client = YouTubeAPIClient()
video = client.get_video_details("6gV22ysoRn8")
if video:
    current_tags = video['snippet'].get('tags', [])
    print(f"Current tags count: {len(current_tags)}")
    print(f"Current tags: {current_tags}")
    
    # Try updating with current tags (should work)
    print("\nTrying to update with same tags...")
    result = client.update_video_metadata(
        video_id="6gV22ysoRn8",
        title=video['snippet']['title'],
        description=video['snippet']['description'],
        tags=current_tags,
        category_id=video['snippet'].get('categoryId')
    )
    print(f"Result: {result}")

import cv2
import numpy as np
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

def punch_zoom(clip, zoom_from=1.0, zoom_to=1.15, duration=1.5):
    """
    Applies a subtle camera punch/zoom-in effect over a specified duration
    using moviepy v2's internal frame function mapping.
    """
    def zoom_frame(get_frame, t):
        scale = zoom_from + (zoom_to - zoom_from) * min(t / duration, 1.0)
        
        frame = get_frame(t)
        h, w = frame.shape[:2]
        
        new_h, new_w = int(h * scale), int(w * scale)
        resized = cv2.resize(frame, (new_w, new_h))
        
        y = (new_h - h) // 2
        x = (new_w - w) // 2
        return resized[y:y+h, x:x+w]

    return clip.transform(zoom_frame, keep_duration=True)


def create_word_captions(clip_duration, word_timestamps, font="Arial", font_size=36, target_size=(1080, 1920)):
    """
    Generates a list of TextClips for word-level animated captions.
    Bypasses raw HTML rendering bugs by splitting the text into two clean blocks 
    or using native MoviePy v2 parameters.
    """
    caption_clips = []
    video_w, video_h = target_size

    current_phrase = []
    max_phrase_words = 5 
    phrases = []

    for word_info in word_timestamps:
        if len(current_phrase) == 0:
            current_phrase.append(word_info)
        else:
            time_gap = word_info['start'] - current_phrase[-1]['end']
            if len(current_phrase) >= max_phrase_words or time_gap > 0.8:
                phrases.append(list(current_phrase))
                current_phrase = [word_info]
            else:
                current_phrase.append(word_info)
                
    if current_phrase:
        phrases.append(current_phrase)

    for phrase in phrases:
        for active_word_info in phrase:
            # Create a clean plain text sentence without any raw HTML tags breaking the view
            plain_text_words = [w['word'] for w in phrase]
            full_text_plain = " ".join(plain_text_words)
            
            w_start = active_word_info['start']
            w_end = active_word_info['end']

            # Base Subtitle Line (White text with black stroke outline)
            try:
                base_txt_clip = TextClip(
                    text=full_text_plain,
                    font=font,
                    font_size=font_size,
                    color='white',  # Set text color natively here
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(video_w - 100, None)
                )
            except Exception:
                base_txt_clip = TextClip(
                    text=full_text_plain,
                    font=None, 
                    font_size=font_size,
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(video_w - 100, None)
                )

            # Highlight Layer: To satisfy "Word highlight" requirement without complex Pango dependencies[cite: 35, 36], 
            # we isolate the single active word token during its exact timestamp window
            active_word_text = active_word_info['word']
            try:
                highlight_clip = TextClip(
                    text=active_word_text,
                    font=font,
                    font_size=font_size + 2, # Slightly bigger "pop-in" effect [cite: 35]
                    color='yellow', # Highlight color [cite: 35]
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(video_w - 100, None)
                )
            except Exception:
                highlight_clip = TextClip(
                    text=active_word_text,
                    font=None,
                    font_size=font_size + 2,
                    color='yellow',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(video_w - 100, None)
                )

            # Position both elements cleanly in the lower 1/3 of the frame [cite: 35]
            base_txt_clip = (base_txt_clip
                             .with_start(w_start)
                             .with_end(w_end)
                             .with_position(('center', int(video_h * 0.75))))
            
            # The highlighted active word pops up right above or perfectly centered over the timeline
            highlight_clip = (highlight_clip
                              .with_start(w_start)
                              .with_end(w_end)
                       
                              .with_position(('center', int(video_h * 0.68))))

            caption_clips.append(base_txt_clip)
            caption_clips.append(highlight_clip)

    return caption_clips


def apply_effects_pipeline(video_clip, word_timestamps, should_zoom=True):
    """
    Master pipeline runner for your effects module. Combines zoom updates 
    and word highlights onto the final vertical layout composition.
    """
    processed_clip = video_clip
    
    if should_zoom:
        processed_clip = punch_zoom(processed_clip, zoom_from=1.0, zoom_to=1.15, duration=1.5)
        
    caption_clips = create_word_captions(
        clip_duration=processed_clip.duration, 
        word_timestamps=word_timestamps,
        target_size=processed_clip.size
    )
    
    final_composition = CompositeVideoClip([processed_clip] + caption_clips)
    return final_composition
# Tao Blog writings: CMS import report

Source: WordPress REST dump (thetaoblog.com), 20 posts in writings.html order. Body char counts are of the cleaned HTML.

## Summary

- Posts: 20
- With cover image: 16 (15 downloaded from WordPress + 1 site image for the featured post)
- No cover image (null): breath-as-a-convergence-point, relaxing-the-nervous-system, what-is-taoism-2, why-taoism-3
- Inline images beyond the leading one: 0
- No iframes, embeds, tables, real headings (h1-h6), blockquotes, or text links in any of the 20 bodies.
- Only one image was downscaled: staying-centered (1320x1822 -> 1159x1600). All others were already under 1600px.
- Bodies contain only <p>, <strong>, <ul>, <li>.

## Per post

### 01. Taoist Calm: A Systems-Level Orientation (`taoist-calm-a-systems-level-orientation`)
- Body: 1937 chars
- Cover: assets/img/events-retreat.jpg
- WordPress leading image dropped per instruction (http://thetaoblog.com/wp-content/uploads/2023/02/FC9688ED-B961-4C6F-88D3-0AD9F74B7FE5.jpeg)
- removed title-repeat paragraph #1: "Taoist Calm: A Systems-Level Orientation"
- cover is the site's own events-retreat.jpg, copied byte-for-byte from the-tao-blog/assets/img (828x552, still carries its EXIF/Photoshop metadata; not re-encoded)

### 02. The Body Knows (`the-body-knows`)
- Body: 1448 chars
- Cover: assets/img/posts/the-body-knows.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2024/02/IMG_6928.jpeg 750x1127 -> 750x1127
- first paragraph kept (not an exact title repeat): "The Body Knows Before the Mind Slows"
- non-ASCII chars: ’ U+2019 “ U+201C ” U+201D
- cover photo has a visible photographer watermark and seal ("Photo©Kai Hirai") in the lower right

### 03. Living Above the Neck (`living-above-the-neck`)
- Body: 1721 chars
- Cover: assets/img/posts/living-above-the-neck.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2024/02/IMG_6614.jpeg 420x650 -> 420x650
- first paragraph kept (not an exact title repeat): "The Cost of Living Above the Neck"
- non-ASCII chars: “ U+201C ” U+201D

### 04. The Modern Stress Paradigm (`the-modern-stress-paradigm`)
- Body: 1537 chars
- Cover: assets/img/posts/the-modern-stress-paradigm.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2021/12/image-4-819x1024-1.jpeg 819x1024 -> 819x1024
- first paragraph kept (not an exact title repeat): "The Modern Stress Paradigm: Regulation Under Pressure"

### 05. Modern Nervous System (`modern-nervous-system`)
- Body: 1518 chars
- Cover: assets/img/posts/modern-nervous-system.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2023/03/50590E62-81C5-46B4-80D2-6DB13B1DB3AE.jpeg 426x640 -> 426x640
- first paragraph kept (not an exact title repeat): "The Modern Nervous System Is Conditioned Against Stillness"

### 06. Meditation and Restlessness (`meditation-and-restlessness`)
- Body: 1206 chars
- Cover: assets/img/posts/meditation-and-restlessness.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2023/03/6457078E-CD1F-41FB-A962-860653D0656B.jpeg 750x562 -> 750x562
- removed title-repeat paragraph #1: "Meditation and Restlessness"

### 07. Gradual Meditation (`gradual-meditation`)
- Body: 2411 chars
- Cover: assets/img/posts/gradual-meditation.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2023/01/4A45FBF1-0279-4C6B-8EBB-33836FCE44B4-683x1024-1.jpeg 683x1024 -> 683x1024
- first paragraph kept (not an exact title repeat): "Meditation Removes Distraction Before It Builds Capacity"
- bold-only paragraphs acting as subheadings (kept as <p><strong>): "Stillness Must Be Earned Gradually"

### 08. Chronic Stimulation (`chronic-stimulation`)
- Body: 1175 chars
- Cover: assets/img/posts/chronic-stimulation.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2023/02/F9417054-D88C-41B8-ADFE-4E2B4AFE6CFF.jpeg 400x600 -> 400x600
- removed title-repeat paragraph #1: "Chronic Stimulation"
- non-ASCII chars: … U+2026

### 09. Calm Energy (`calm-energy`)
- Body: 987 chars
- Cover: assets/img/posts/calm-energy.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2023/05/72CA1D7B-2229-4729-80A2-C30E8224804B.jpeg 480x768 -> 480x768
- removed title line "Calm Energy" from start of first paragraph (was joined by <br>)

### 10. Five-Minute Stillness Practice (`five-minute-stillness-practice`)
- Body: 595 chars
- Cover: assets/img/posts/five-minute-stillness-practice.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2023/11/IMG_4324.jpeg 749x1138 -> 749x1138
- removed title-repeat paragraph #2: "Five-Minute Stillness Practice" (after "PRACTICE SECTION")

### 11. Breath as a Convergence Point (`breath-as-a-convergence-point`)
- Body: 1598 chars
- Cover: none
- removed title-repeat paragraph #1: "Breath as a Convergence Point"
- bold-only paragraphs acting as subheadings (kept as <p><strong>): "The Role of Attention and Awareness"
- non-ASCII chars: – U+2013

### 12. Relaxing the Nervous System (`relaxing-the-nervous-system`)
- Body: 1508 chars
- Cover: none
- empty WordPress gallery block at top (no image) removed
- removed title-repeat paragraph #1: "Relaxing the Nervous System"

### 13. Internal Alchemy (`internal-alchemy-2`)
- Body: 1790 chars
- Cover: assets/img/posts/internal-alchemy.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2023/10/IMG_3833.jpeg 749x635 -> 749x635
- removed title-repeat paragraph #1: "Internal Alchemy"
- signature line "TheTaoBlog.com" kept
- hashtag line kept: "#taoism #taoist #taichi #meditation #yoga"

### 14. Taoist Dreaming (`taoist-dreaming`)
- Body: 1741 chars
- Cover: assets/img/posts/taoist-dreaming.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2026/04/IMG_4446.jpeg 753x764 -> 753x764
- removed title-repeat paragraph #1: "Taoist Dreaming"
- signature line "TheTaoBlog.com" kept
- hashtag line kept: "#taoism #taoist #taichi #meditation #yoga"

### 15. Spring and The Liver (`spring-and-the-liver`)
- Body: 1547 chars
- Cover: assets/img/posts/spring-and-the-liver.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2023/09/Temple-Steps-768x1024-1.jpg 768x1024 -> 768x1024
- removed title-repeat paragraph #1: "Spring and The Liver"

### 16. Flowing with the Seasons (`flowing-with-the-seasons`)
- Body: 1023 chars
- Cover: assets/img/posts/flowing-with-the-seasons.jpg
- leading image caption "Screenshot" dropped
- cover from http://thetaoblog.com/wp-content/uploads/2026/04/IMG_4235-1.jpeg 1320x639 -> 1320x639
- removed title-repeat paragraph #1: "Flowing with the Seasons"
- non-ASCII chars: ’ U+2019
- cover is landscape (1320x639); all other covers are portrait or near-square

### 17. Staying Centered (`staying-centered`)
- Body: 1498 chars
- Cover: assets/img/posts/staying-centered.jpg
- leading image caption "Screenshot" dropped
- cover from http://thetaoblog.com/wp-content/uploads/2026/04/IMG_4219.jpeg 1320x1822 -> 1159x1600
- removed title-repeat paragraph #1: "Staying Centered"
- non-ASCII chars: ’ U+2019

### 18. What is Taoism? (`what-is-taoism-2`)
- Body: 2256 chars
- Cover: none
- removed title-repeat paragraph #1: "What is Taoism?"
- run-together word "withintheir" is in the WordPress source itself (not from &nbsp; removal); left unchanged
- non-ASCII chars: ’ U+2019

### 19. Why Taoism? (`why-taoism-3`)
- Body: 1029 chars
- Cover: none
- removed title-repeat paragraph #1: "Why Taoism?"
- non-ASCII chars: ’ U+2019

### 20. Where Should I Start? (`where-should-i-start-2`)
- Body: 1590 chars
- Cover: assets/img/posts/where-should-i-start.jpg
- cover from http://thetaoblog.com/wp-content/uploads/2023/08/BE21ABFB-9B1D-4861-830E-11E8485F8A37.jpeg 446x450 -> 446x450
- removed title-repeat paragraph #1: "Where Should I Start?"
- run-together word "isreally" is in the WordPress source itself (not from &nbsp; removal); left unchanged
- run-together word "areneither" is in the WordPress source itself (not from &nbsp; removal); left unchanged

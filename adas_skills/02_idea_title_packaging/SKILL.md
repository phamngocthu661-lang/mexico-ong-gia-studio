---
name: adas-idea-title-packaging
description: "Generate, score and package original Japanese story premises, titles and 6-layer high-CTR thumbnail narratives before outlining."
---

# Idea, Title & 6-Layer Thumbnail Packaging Engine

Mục tiêu: biến research thành premise đủ mạnh để đáng viết 90–120 phút; chọn title **trước** khi viết script; đồng thời tạo cấu trúc thumbnail 6 tầng theo visual language của niche Japanese long-form family drama.

## Bắt buộc dùng reference corpus
Đọc `references/corpus_dna.md` và `references/hard_length_contract.md` trước khi thực hiện. Đọc thêm `references/thumbnail_dna_6_layer.md` khi tạo packaging. Các pattern chỉ dùng như benchmark cơ chế; không sao chép exact wording/composition của competitor.

## Input
- `MECHANISM_LIBRARY` + `30_RAW_PREMISES` từ skill 01, hoặc seed topic của người dùng.
- Audience/channel positioning.
- Nếu có ảnh competitor/reference trong Project, dùng chúng để hiểu visual language nhưng không copy nguyên thumbnail.


# HARD LONG-FORM CAPACITY GATE
Trước khi một idea được chọn làm winner, phải chứng minh premise có thể phát triển tự nhiên thành **40,001–50,000 ký tự thuần** theo `hard_length_contract.md`.

Bắt buộc xuất:
- `LONGFORM_CAPACITY: PASS / RISK / FAIL`
- ít nhất 8–12 meaningful turns/scenes có chức năng khác nhau
- ít nhất 3 reveal layers
- đủ consequence/relationship movement để kéo dài mà không lặp filler

Nếu `LONGFORM_CAPACITY != PASS`, idea không được handoff sang STEP 3 dù Idea Score/Title Score cao.

## 1. Tạo premise bằng ma trận
Kết hợp 4 chiều:
- RELATION: 母娘 / 父娘 / 夫婦 / 元夫婦 / 義母嫁 / 兄妹 / 姉妹 / 祖父母 / 婚約者 / 親子
- SETTING: 病院 / 銀行 / 同窓会 / 葬儀 / 結婚式 / 正月 / お盆 / 実家 / マンション / 学校 / 旅館
- PROOF OBJECT: 手紙 / 通帳 / 写真 / 鍵 / バッグ / 箱 / 領収書 / 指輪 / 古い携帯 / 病院書類
- EMOTION: 恩返し / 後悔 / 裏切り / 誤解 / 再会 / 嫉妬 / 犠牲 / 尊厳 / 許し

## 2. Idea Score — 100
- Curiosity gap 20
- Emotional stake 20
- Relatability of relationship 15
# meikipop/ocr/providers/postprocessing.py
import logging
import statistics
from typing import List, Tuple

from meikipop.config.config import config
from meikipop.ocr.interface import Paragraph, Word, BoundingBox

logger = logging.getLogger(__name__)

FURIGANA_VERTICAL_WIDTH_THRESHOLD = 0.65
FURIGANA_HORIZONTAL_HEIGHT_THRESHOLD = 0.65
# measured on manga scans: furigana columns are 0.64-0.70x the median column width, text columns 0.85x or more
MANGA_FURIGANA_VERTICAL_WIDTH_THRESHOLD = 0.8


def _merge_bounding_boxes(boxes: List[BoundingBox]) -> BoundingBox:
    """Creates a single BoundingBox that encompasses all provided boxes."""
    if not boxes:
        return BoundingBox(0, 0, 0, 0)

    min_x = min(b.center_x - b.width / 2 for b in boxes)
    max_x = max(b.center_x + b.width / 2 for b in boxes)
    min_y = min(b.center_y - b.height / 2 for b in boxes)
    max_y = max(b.center_y + b.height / 2 for b in boxes)

    width = max_x - min_x
    height = max_y - min_y
    center_x = min_x + width / 2
    center_y = min_y + height / 2

    return BoundingBox(center_x, center_y, width, height)


def _are_lines_adjacent(line1: Paragraph, line2: Paragraph) -> bool:
    """
    Determines if two lines are close enough to be considered part of the same paragraph.
    This uses heuristics to be tolerant of small OCR inaccuracies.
    """
    b1, b2 = line1.box, line2.box
    is_vertical = line1.is_vertical

    if is_vertical:
        # For vertical text (read R->L), lines should have significant y-overlap
        # and be close on the x-axis.
        y_overlap = max(0,
                        min(b1.center_y + b1.height / 2, b2.center_y + b2.height / 2) - max(b1.center_y - b1.height / 2,
                                                                                            b2.center_y - b2.height / 2))
        has_enough_overlap = y_overlap > (min(b1.height, b2.height) * 0.5)

        # Check horizontal distance between line centers. Allow up to 1.9x the width of a line for spacing.
        horizontal_distance_ok = abs(b1.center_x - b2.center_x) < 1.9 * max(b1.width, b2.width)
        return has_enough_overlap and horizontal_distance_ok
    else:
        # For horizontal text (read T->B), lines should have significant x-overlap
        # and be close on the y-axis.
        x_overlap = max(0, min(b1.center_x + b1.width / 2, b2.center_x + b2.width / 2) - max(b1.center_x - b1.width / 2,
                                                                                             b2.center_x - b2.width / 2))
        has_enough_overlap = x_overlap > (min(b1.width, b2.width) * 0.5)

        # Check vertical distance. Allow up to 1.9x the height for line spacing.
        vertical_distance_ok = abs(b1.center_y - b2.center_y) < 1.9 * max(b1.height, b2.height)
        return has_enough_overlap and vertical_distance_ok


def _merge_lines_into_paragraph(lines: List[Paragraph]) -> Paragraph:
    """Merges a list of single-line Paragraphs into one cohesive Paragraph."""
    if not lines:
        return None

    is_vertical = lines[0].is_vertical

    if is_vertical:
        # Vertical text is read right-to-left
        lines.sort(key=lambda p: p.box.center_x, reverse=True)
    else:
        # Horizontal text is read top-to-bottom
        lines.sort(key=lambda p: p.box.center_y)

    all_words: List[Word] = []
    full_text_parts: List[str] = []
    all_boxes: List[BoundingBox] = []

    for line in lines:
        all_words.extend(line.words)
        full_text_parts.append(line.full_text)
        all_boxes.append(line.box)

    full_text = "".join(full_text_parts)
    merged_box = _merge_bounding_boxes(all_boxes)

    return Paragraph(
        full_text=full_text,
        words=all_words,
        box=merged_box,
        is_vertical=is_vertical
    )


def _drop_rows_across_columns(lines: List[Paragraph]) -> List[Paragraph]:
    """
    Manga mode: Chrome Screen AI often reads tightly packed vertical text a second time sideways, returning extra
    horizontal "lines" that cut across the real columns (e.g. モ使そ from それで / 使える / モンか).
    Drops horizontal lines whose characters mostly sit inside vertical lines, so lookups and translations use the columns.
    shortcut: only removes rows that duplicate detected columns; if an engine ever returns the rows without the
    columns, those rows would need to be rebuilt into columns instead.
    """
    columns = [line.box for line in lines if line.is_vertical]
    if not columns:
        return lines

    def inside(b: BoundingBox, c: BoundingBox) -> bool:
        return abs(b.center_x - c.center_x) <= c.width / 2 and abs(b.center_y - c.center_y) <= c.height / 2

    def cuts_across_columns(line: Paragraph) -> bool:
        hits = sum(any(inside(w.box, c) for c in columns) for w in line.words)
        return hits * 2 > len(line.words)

    kept = [line for line in lines if line.is_vertical or not line.words or not cuts_across_columns(line)]
    if len(kept) < len(lines):
        logger.debug(f"Dropped {len(lines) - len(kept)} horizontal lines that cut across vertical text.")
    return kept


# NEW FUNCTION TO DETECT FURIGANA
def _classify_lines_by_size(
        lines: List[Paragraph]
) -> Tuple[List[Paragraph], List[Paragraph]]:
    """
    Separates lines into main text and furigana based on their size.

    Furigana is much smaller than the main text. This function calculates the
    median size (width for vertical, height for horizontal) and classifies
    any significantly smaller lines as furigana.

    Returns:
        A tuple containing two lists: (main_lines, furigana_lines).
    """
    main_lines: List[Paragraph] = []
    furigana_lines: List[Paragraph] = []

    vertical_lines = [p for p in lines if p.is_vertical]
    horizontal_lines = [p for p in lines if not p.is_vertical]

    if vertical_lines:
        # For vertical text, furigana lines are much thinner (smaller width)
        widths = [p.box.width for p in vertical_lines]
        if len(widths) > 1:
            median_width = statistics.median(widths)
            ratio = MANGA_FURIGANA_VERTICAL_WIDTH_THRESHOLD if config.text_mode == 'manga' \
                else FURIGANA_VERTICAL_WIDTH_THRESHOLD
            threshold = median_width * ratio
            for line in vertical_lines:
                if line.box.width < threshold:
                    furigana_lines.append(line)
                else:
                    main_lines.append(line)
        else:
            # If there's only one line, it's main text by definition
            main_lines.extend(vertical_lines)

    if horizontal_lines:
        # For horizontal text, furigana lines are much shorter (smaller height)
        heights = [p.box.height for p in horizontal_lines]
        if len(heights) > 1:
            median_height = statistics.median(heights)
            threshold = median_height * FURIGANA_HORIZONTAL_HEIGHT_THRESHOLD
            for line in horizontal_lines:
                if line.box.height < threshold:
                    furigana_lines.append(line)
                else:
                    main_lines.append(line)
        else:
            main_lines.extend(horizontal_lines)

    return main_lines, furigana_lines


def group_lines_into_paragraphs(lines: List[Paragraph]) -> List[Paragraph]:
    """
    Takes a flat list of single-line Paragraphs and groups them into
    multi-line Paragraphs based on proximity and orientation.

    This version includes a preprocessing step to identify and separate
    furigana, which is then excluded from the main paragraph grouping logic.
    """
    if not lines:
        return []

    if config.text_mode == 'manga':
        lines = _drop_rows_across_columns(lines)

    # Classify lines into main text and furigana
    main_lines, furigana_lines = _classify_lines_by_size(lines)
    logger.debug(f"Identified and separated {len(furigana_lines)} furigana lines.")

    # Separate main lines by orientation for processing
    vertical_lines = [p for p in main_lines if p.is_vertical]
    horizontal_lines = [p for p in main_lines if not p.is_vertical]

    processed_paragraphs = []

    for line_set in [vertical_lines, horizontal_lines]:
        while line_set:
            current_group = [line_set.pop(0)]
            i = 0
            while i < len(line_set):
                line_to_check = line_set[i]
                is_adjacent_to_group = any(
                    _are_lines_adjacent(grouped_line, line_to_check) for grouped_line in current_group)

                if is_adjacent_to_group:
                    current_group.append(line_set.pop(i))
                    # Restart check from the beginning since the group has grown
                    i = 0
                else:
                    i += 1

            merged_para = _merge_lines_into_paragraph(current_group)
            if merged_para:
                processed_paragraphs.append(merged_para)

    # Add the isolated furigana lines back as their own separate paragraphs
    final_paragraphs = processed_paragraphs + furigana_lines

    logger.debug(f"Regrouped {len(lines)} raw OCR lines into {len(final_paragraphs)} paragraphs.")
    return final_paragraphs

from docbridge.detect import detect_language
from docbridge.thai import normalize_thai, segment


def test_sara_am_repair():
    broken = "ทำ".replace("ำ", "ํา")  # nikhahit + sara aa
    assert normalize_thai(broken) == "ทำ"


def test_zero_width_and_doubled_marks_removed():
    assert normalize_thai("ก​า​ร") == "การ"
    assert normalize_thai("ก่่าว") == "ก่าว"


def test_letter_spaced_extraction_is_collapsed():
    assert normalize_thai("ก า ร ท ด ส อ บ ภ า ษ า") == "การทดสอบภาษา"


def test_normal_thai_spacing_untouched():
    s = "บริษัทมีรายได้เพิ่มขึ้น โดยเฉพาะสินค้าแช่เย็น"
    assert normalize_thai(s) == s


def test_english_untouched():
    s = "Hello  world, 123"
    assert normalize_thai(s) == s


def test_thai_digits_opt_in():
    assert normalize_thai("ราคา ๑๒๐ บาท") == "ราคา ๑๒๐ บาท"
    assert normalize_thai("ราคา ๑๒๐ บาท", thai_digits=True) == "ราคา 120 บาท"


def test_language_detection():
    assert detect_language("รายงานยอดขายประจำไตรมาส")[0] == "th"
    assert detect_language("Quarterly sales report")[0] == "en"
    assert detect_language("รายงาน Quarterly Report ประจำปี sales")[0] == "mixed"
    assert detect_language("123 456")[0] == "unknown"


def test_segmentation():
    words = segment("ฉันกินข้าวที่บ้าน")
    assert "บ้าน" in words and len(words) >= 3

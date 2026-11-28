import pytest
from app.services.ocr import TesseractBetSlipOCR

def test_ocr_adapter_rejects_empty_and_oversized_images_before_processing():
 ocr=TesseractBetSlipOCR(max_image_bytes=4,max_pixels=100)
 with pytest.raises(ValueError,match="empty"):ocr.extract_and_reconstruct(b"")
 with pytest.raises(ValueError,match="byte limit"):ocr.extract_and_reconstruct(b"12345")

def test_ocr_adapter_rejects_unsupported_image_bytes():
 ocr=TesseractBetSlipOCR()
 with pytest.raises(ValueError):ocr.extract_and_reconstruct(b"not-an-image")

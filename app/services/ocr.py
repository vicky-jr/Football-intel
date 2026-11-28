"""Optional Tesseract/Pillow image OCR adapter for bookmaker bet-slip screenshots.

The original image is processed in memory and is not written to disk. The caller
must obtain user consent before sending screenshots to this local OCR component.
"""
from __future__ import annotations
from io import BytesIO
import hashlib
from typing import Any

from app.services.bet_slip import reconstruct_bet_slip

class TesseractBetSlipOCR:
    ALLOWED_FORMATS={"PNG","JPEG","WEBP"}
    def __init__(self,max_image_bytes:int=5*1024*1024,max_pixels:int=20_000_000)->None:
        if max_image_bytes<1 or max_pixels<1:raise ValueError("image limits must be positive")
        self.max_image_bytes=max_image_bytes;self.max_pixels=max_pixels

    def extract_and_reconstruct(self,image_bytes:bytes,*,stake:float|None=None)->dict[str,Any]:
        if not image_bytes:raise ValueError("image is empty")
        if len(image_bytes)>self.max_image_bytes:raise ValueError("image exceeds configured byte limit")
        try:
            from PIL import Image,ImageOps
            import pytesseract
            from pytesseract import Output
        except ImportError as exc:
            raise RuntimeError("optional OCR dependencies are missing; install Pillow and pytesseract") from exc

        try:
            with Image.open(BytesIO(image_bytes)) as opened:
                image_format=opened.format
                width,height=opened.size
                if image_format not in self.ALLOWED_FORMATS:raise ValueError("unsupported image format")
                if width*height>self.max_pixels:raise ValueError("image exceeds configured pixel limit")
                image=ImageOps.autocontrast(ImageOps.grayscale(opened.convert("RGB")))
                data=pytesseract.image_to_data(image,config="--psm 6",output_type=Output.DICT)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"image could not be decoded or OCR failed: {type(exc).__name__}") from exc

        tokens=[]
        confidences=[]
        for token,raw_conf in zip(data.get("text",[]),data.get("conf",[])):
            token=str(token).strip()
            try:confidence=float(raw_conf)
            except (TypeError,ValueError):confidence=-1
            if token:
                tokens.append(token)
                if confidence>=0:confidences.append(confidence)
        extracted_text=" ".join(tokens)
        # Reflow token stream by the OCR block/paragraph/line identifiers to
        # preserve selection rows rather than forcing all tokens onto one line.
        line_groups={}
        for index,token in enumerate(data.get("text",[])):
            token=str(token).strip()
            if not token:continue
            key=tuple(data.get(field,[])[index] for field in ("block_num","par_num","line_num"))
            line_groups.setdefault(key,[]).append(token)
        lines=[" ".join(values) for _,values in sorted(line_groups.items())]
        extracted_text="\n".join(lines).strip() or extracted_text
        result=reconstruct_bet_slip(
            extracted_text,image_sha256=hashlib.sha256(image_bytes).hexdigest(),stake=stake
        )
        result["extraction_method"]="tesseract_ocr"
        result["image_metadata"]={"format":image_format,"width":width,"height":height,
                                  "bytes":len(image_bytes)}
        result["mean_ocr_token_confidence"]=(
            round(sum(confidences)/len(confidences),2) if confidences else None
        )
        result["limitations"].append(
            "OCR confidence is not semantic certainty; each selection must still be checked against the bookmaker slip."
        )
        return result

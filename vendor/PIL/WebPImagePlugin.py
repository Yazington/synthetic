# coding: utf-8
from __future__ import annotations
from io import BytesIO
from typing import IO, Any
from . import Image, ImageFile
try:
    from . import _webp
    SUPPORTED = True
except ImportError:
    SUPPORTED = False
_VP8_MODES_BY_IDENTIFIER = {b'VP8 ': 'RGB', b'VP8X': 'RGBA', b'VP8L': 'RGBA'}

def _accept(prefix: bytes) -> bool | str:
    is_riff_file_format = prefix[:4] == b'RIFF'
    is_webp_file = prefix[8:12] == b'WEBP'
    is_valid_vp8_mode = prefix[12:16] in _VP8_MODES_BY_IDENTIFIER
    if is_riff_file_format and is_webp_file and is_valid_vp8_mode:
        if not SUPPORTED:
            return 'image file could not be identified because WEBP support not installed'
        return True
    return False

class WebPImageFile(ImageFile.ImageFile):
    format = 'WEBP'
    format_description = 'WebP image'
    __loaded = 0
    __logical_frame = 0

    def _open(self) -> None:
        self._decoder = _webp.WebPAnimDecoder(self.fp.read())
        (width, height, loop_count, bgcolor, frame_count, mode) = self._decoder.get_info()
        self._size = (width, height)
        self.info['loop'] = loop_count
        (bg_a, bg_r, bg_g, bg_b) = (bgcolor >> 24 & 255, bgcolor >> 16 & 255, bgcolor >> 8 & 255, bgcolor & 255)
        self.info['background'] = (bg_r, bg_g, bg_b, bg_a)
        self.n_frames = frame_count
        self.is_animated = self.n_frames > 1
        self._mode = 'RGB' if mode == 'RGBX' else mode
        self.rawmode = mode
        self.tile = []
        icc_profile = self._decoder.get_chunk('ICCP')
        exif = self._decoder.get_chunk('EXIF')
        xmp = self._decoder.get_chunk('XMP ')
        if icc_profile:
            self.info['icc_profile'] = icc_profile
        if exif:
            self.info['exif'] = exif
        if xmp:
            self.info['xmp'] = xmp
        self._reset(reset=False)

    def _getexif(self) -> dict[int, Any] | None:
        if 'exif' not in self.info:
            return None
        return self.getexif()._get_merged_dict()

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return
        self.__logical_frame = frame

    def _reset(self, reset: bool=True) -> None:
        if reset:
            self._decoder.reset()
        self.__physical_frame = 0
        self.__loaded = -1
        self.__timestamp = 0

    def _get_next(self) -> tuple[bytes, int, int]:
        ret = self._decoder.get_next()
        self.__physical_frame += 1
        if ret is None:
            self._reset()
            self.seek(0)
            msg = 'failed to decode next frame in WebP file'
            raise EOFError(msg)
        (data, timestamp) = ret
        duration = timestamp - self.__timestamp
        self.__timestamp = timestamp
        timestamp -= duration
        return (data, timestamp, duration)

    def _seek(self, frame: int) -> None:
        if self.__physical_frame == frame:
            return
        if frame < self.__physical_frame:
            self._reset()
        while self.__physical_frame < frame:
            self._get_next()

    def load(self) -> Image.core.PixelAccess | None:
        if self.__loaded != self.__logical_frame:
            self._seek(self.__logical_frame)
            (data, timestamp, duration) = self._get_next()
            self.info['timestamp'] = timestamp
            self.info['duration'] = duration
            self.__loaded = self.__logical_frame
            if self.fp and self._exclusive_fp:
                self.fp.close()
            self.fp = BytesIO(data)
            self.tile = [ImageFile._Tile('raw', (0, 0) + self.size, 0, self.rawmode)]
        return super().load()

    def load_seek(self, pos: int) -> None:
        pass

    def tell(self) -> int:
        return self.__logical_frame

def _convert_frame(im: Image.Image) -> Image.Image:
    if im.mode not in ('RGBX', 'RGBA', 'RGB'):
        im = im.convert('RGBA' if im.has_transparency_data else 'RGB')
    return im

def _save_all(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    encoderinfo = im.encoderinfo.copy()
    append_images = list(encoderinfo.get('append_images', []))
    total = 0
    for ims in [im] + append_images:
        total += getattr(ims, 'n_frames', 1)
    if total == 1:
        _save(im, fp, filename)
        return
    background: int | tuple[int, ...] = (0, 0, 0, 0)
    if 'background' in encoderinfo:
        background = encoderinfo['background']
    elif 'background' in im.info:
        background = im.info['background']
        if isinstance(background, int):
            palette = im.getpalette()
            if palette:
                (r, g, b) = palette[background * 3:(background + 1) * 3]
                background = (r, g, b, 255)
            else:
                background = (background, background, background, 255)
    duration = im.encoderinfo.get('duration', im.info.get('duration', 0))
    loop = im.encoderinfo.get('loop', 0)
    minimize_size = im.encoderinfo.get('minimize_size', False)
    kmin = im.encoderinfo.get('kmin', None)
    kmax = im.encoderinfo.get('kmax', None)
    allow_mixed = im.encoderinfo.get('allow_mixed', False)
    verbose = False
    lossless = im.encoderinfo.get('lossless', False)
    quality = im.encoderinfo.get('quality', 80)
    alpha_quality = im.encoderinfo.get('alpha_quality', 100)
    method = im.encoderinfo.get('method', 0)
    icc_profile = im.encoderinfo.get('icc_profile') or ''
    exif = im.encoderinfo.get('exif', '')
    if isinstance(exif, Image.Exif):
        exif = exif.tobytes()
    xmp = im.encoderinfo.get('xmp', '')
    if allow_mixed:
        lossless = False
    if kmin is None:
        kmin = 9 if lossless else 3
    if kmax is None:
        kmax = 17 if lossless else 5
    if not isinstance(background, (list, tuple)) or len(background) != 4 or (not all((0 <= v < 256 for v in background))):
        msg = f'Background color is not an RGBA tuple clamped to (0-255): {background}'
        raise OSError(msg)
    (bg_r, bg_g, bg_b, bg_a) = background
    background = bg_a << 24 | bg_r << 16 | bg_g << 8 | bg_b << 0
    enc = _webp.WebPAnimEncoder(im.size[0], im.size[1], background, loop, minimize_size, kmin, kmax, allow_mixed, verbose)
    frame_idx = 0
    timestamp = 0
    cur_idx = im.tell()
    try:
        for ims in [im] + append_images:
            nfr = getattr(ims, 'n_frames', 1)
            for idx in range(nfr):
                ims.seek(idx)
                frame = _convert_frame(ims)
                enc.add(frame.getim(), round(timestamp), lossless, quality, alpha_quality, method)
                if isinstance(duration, (list, tuple)):
                    timestamp += duration[frame_idx]
                else:
                    timestamp += duration
                frame_idx += 1
    finally:
        im.seek(cur_idx)
    enc.add(None, round(timestamp), lossless, quality, alpha_quality, 0)
    data = enc.assemble(icc_profile, exif, xmp)
    if data is None:
        msg = 'cannot write file as WebP (encoder returned None)'
        raise OSError(msg)
    fp.write(data)

def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    lossless = im.encoderinfo.get('lossless', False)
    quality = im.encoderinfo.get('quality', 80)
    alpha_quality = im.encoderinfo.get('alpha_quality', 100)
    icc_profile = im.encoderinfo.get('icc_profile') or ''
    exif = im.encoderinfo.get('exif', b'')
    if isinstance(exif, Image.Exif):
        exif = exif.tobytes()
    if exif.startswith(b'Exif\x00\x00'):
        exif = exif[6:]
    xmp = im.encoderinfo.get('xmp', '')
    method = im.encoderinfo.get('method', 4)
    exact = 1 if im.encoderinfo.get('exact') else 0
    im = _convert_frame(im)
    data = _webp.WebPEncode(im.getim(), lossless, float(quality), float(alpha_quality), icc_profile, method, exact, exif, xmp)
    if data is None:
        msg = 'cannot write file as WebP (encoder returned None)'
        raise OSError(msg)
    fp.write(data)
Image.register_open(WebPImageFile.format, WebPImageFile, _accept)
if SUPPORTED:
    Image.register_save(WebPImageFile.format, _save)
    Image.register_save_all(WebPImageFile.format, _save_all)
    Image.register_extension(WebPImageFile.format, '.webp')
    Image.register_mime(WebPImageFile.format, 'image/webp')

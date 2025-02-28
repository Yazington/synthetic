# coding: utf-8
from __future__ import annotations
import itertools
import os
import struct
from typing import IO, Any, cast
from . import Image, ImageFile, ImageSequence, JpegImagePlugin, TiffImagePlugin
from ._binary import o32le

def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    JpegImagePlugin._save(im, fp, filename)

def _save_all(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    append_images = im.encoderinfo.get('append_images', [])
    if not append_images and (not getattr(im, 'is_animated', False)):
        _save(im, fp, filename)
        return
    mpf_offset = 28
    offsets: list[int] = []
    for imSequence in itertools.chain([im], append_images):
        for im_frame in ImageSequence.Iterator(imSequence):
            if not offsets:
                im_frame.encoderinfo['extra'] = b'\xff\xe2' + struct.pack('>H', 6 + 82) + b'MPF\x00' + b' ' * 82
                exif = im_frame.encoderinfo.get('exif')
                if isinstance(exif, Image.Exif):
                    exif = exif.tobytes()
                    im_frame.encoderinfo['exif'] = exif
                if exif:
                    mpf_offset += 4 + len(exif)
                JpegImagePlugin._save(im_frame, fp, filename)
                offsets.append(fp.tell())
            else:
                im_frame.save(fp, 'JPEG')
                offsets.append(fp.tell() - offsets[-1])
    ifd = TiffImagePlugin.ImageFileDirectory_v2()
    ifd[45056] = b'0100'
    ifd[45057] = len(offsets)
    mpentries = b''
    data_offset = 0
    for (i, size) in enumerate(offsets):
        if i == 0:
            mptype = 196608
        else:
            mptype = 0
        mpentries += struct.pack('<LLLHH', mptype, size, data_offset, 0, 0)
        if i == 0:
            data_offset -= mpf_offset
        data_offset += size
    ifd[45058] = mpentries
    fp.seek(mpf_offset)
    fp.write(b'II*\x00' + o32le(8) + ifd.tobytes(8))
    fp.seek(0, os.SEEK_END)

class MpoImageFile(JpegImagePlugin.JpegImageFile):
    format = 'MPO'
    format_description = 'MPO (CIPA DC-007)'
    _close_exclusive_fp_after_loading = False

    def _open(self) -> None:
        self.fp.seek(0)
        JpegImagePlugin.JpegImageFile._open(self)
        self._after_jpeg_open()

    def _after_jpeg_open(self, mpheader: dict[int, Any] | None=None) -> None:
        self.mpinfo = mpheader if mpheader is not None else self._getmp()
        if self.mpinfo is None:
            msg = 'Image appears to be a malformed MPO file'
            raise ValueError(msg)
        self.n_frames = self.mpinfo[45057]
        self.__mpoffsets = [mpent['DataOffset'] + self.info['mpoffset'] for mpent in self.mpinfo[45058]]
        self.__mpoffsets[0] = 0
        assert self.n_frames == len(self.__mpoffsets)
        del self.info['mpoffset']
        self.is_animated = self.n_frames > 1
        self._fp = self.fp
        self._fp.seek(self.__mpoffsets[0])
        self.__frame = 0
        self.offset = 0
        self.readonly = 1

    def load_seek(self, pos: int) -> None:
        self._fp.seek(pos)

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return
        self.fp = self._fp
        self.offset = self.__mpoffsets[frame]
        original_exif = self.info.get('exif')
        if 'exif' in self.info:
            del self.info['exif']
        self.fp.seek(self.offset + 2)
        if not self.fp.read(2):
            msg = 'No data found for frame'
            raise ValueError(msg)
        self.fp.seek(self.offset)
        JpegImagePlugin.JpegImageFile._open(self)
        if self.info.get('exif') != original_exif:
            self._reload_exif()
        self.tile = [ImageFile._Tile('jpeg', (0, 0) + self.size, self.offset, self.tile[0][-1])]
        self.__frame = frame

    def tell(self) -> int:
        return self.__frame

    @staticmethod
    def adopt(jpeg_instance: JpegImagePlugin.JpegImageFile, mpheader: dict[int, Any] | None=None) -> MpoImageFile:
        """
        Transform the instance of JpegImageFile into
        an instance of MpoImageFile.
        After the call, the JpegImageFile is extended
        to be an MpoImageFile.

        This is essentially useful when opening a JPEG
        file that reveals itself as an MPO, to avoid
        double call to _open.
        """
        jpeg_instance.__class__ = MpoImageFile
        mpo_instance = cast(MpoImageFile, jpeg_instance)
        mpo_instance._after_jpeg_open(mpheader)
        return mpo_instance
Image.register_save(MpoImageFile.format, _save)
Image.register_save_all(MpoImageFile.format, _save_all)
Image.register_extension(MpoImageFile.format, '.mpo')
Image.register_mime(MpoImageFile.format, 'image/mpo')

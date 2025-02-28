# coding: utf-8
from __future__ import annotations
from typing import IO
from . import Image, ImageFile
from ._binary import o8
from ._binary import o16be as o16b
_Palm8BitColormapValues = ((255, 255, 255), (255, 204, 255), (255, 153, 255), (255, 102, 255), (255, 51, 255), (255, 0, 255), (255, 255, 204), (255, 204, 204), (255, 153, 204), (255, 102, 204), (255, 51, 204), (255, 0, 204), (255, 255, 153), (255, 204, 153), (255, 153, 153), (255, 102, 153), (255, 51, 153), (255, 0, 153), (204, 255, 255), (204, 204, 255), (204, 153, 255), (204, 102, 255), (204, 51, 255), (204, 0, 255), (204, 255, 204), (204, 204, 204), (204, 153, 204), (204, 102, 204), (204, 51, 204), (204, 0, 204), (204, 255, 153), (204, 204, 153), (204, 153, 153), (204, 102, 153), (204, 51, 153), (204, 0, 153), (153, 255, 255), (153, 204, 255), (153, 153, 255), (153, 102, 255), (153, 51, 255), (153, 0, 255), (153, 255, 204), (153, 204, 204), (153, 153, 204), (153, 102, 204), (153, 51, 204), (153, 0, 204), (153, 255, 153), (153, 204, 153), (153, 153, 153), (153, 102, 153), (153, 51, 153), (153, 0, 153), (102, 255, 255), (102, 204, 255), (102, 153, 255), (102, 102, 255), (102, 51, 255), (102, 0, 255), (102, 255, 204), (102, 204, 204), (102, 153, 204), (102, 102, 204), (102, 51, 204), (102, 0, 204), (102, 255, 153), (102, 204, 153), (102, 153, 153), (102, 102, 153), (102, 51, 153), (102, 0, 153), (51, 255, 255), (51, 204, 255), (51, 153, 255), (51, 102, 255), (51, 51, 255), (51, 0, 255), (51, 255, 204), (51, 204, 204), (51, 153, 204), (51, 102, 204), (51, 51, 204), (51, 0, 204), (51, 255, 153), (51, 204, 153), (51, 153, 153), (51, 102, 153), (51, 51, 153), (51, 0, 153), (0, 255, 255), (0, 204, 255), (0, 153, 255), (0, 102, 255), (0, 51, 255), (0, 0, 255), (0, 255, 204), (0, 204, 204), (0, 153, 204), (0, 102, 204), (0, 51, 204), (0, 0, 204), (0, 255, 153), (0, 204, 153), (0, 153, 153), (0, 102, 153), (0, 51, 153), (0, 0, 153), (255, 255, 102), (255, 204, 102), (255, 153, 102), (255, 102, 102), (255, 51, 102), (255, 0, 102), (255, 255, 51), (255, 204, 51), (255, 153, 51), (255, 102, 51), (255, 51, 51), (255, 0, 51), (255, 255, 0), (255, 204, 0), (255, 153, 0), (255, 102, 0), (255, 51, 0), (255, 0, 0), (204, 255, 102), (204, 204, 102), (204, 153, 102), (204, 102, 102), (204, 51, 102), (204, 0, 102), (204, 255, 51), (204, 204, 51), (204, 153, 51), (204, 102, 51), (204, 51, 51), (204, 0, 51), (204, 255, 0), (204, 204, 0), (204, 153, 0), (204, 102, 0), (204, 51, 0), (204, 0, 0), (153, 255, 102), (153, 204, 102), (153, 153, 102), (153, 102, 102), (153, 51, 102), (153, 0, 102), (153, 255, 51), (153, 204, 51), (153, 153, 51), (153, 102, 51), (153, 51, 51), (153, 0, 51), (153, 255, 0), (153, 204, 0), (153, 153, 0), (153, 102, 0), (153, 51, 0), (153, 0, 0), (102, 255, 102), (102, 204, 102), (102, 153, 102), (102, 102, 102), (102, 51, 102), (102, 0, 102), (102, 255, 51), (102, 204, 51), (102, 153, 51), (102, 102, 51), (102, 51, 51), (102, 0, 51), (102, 255, 0), (102, 204, 0), (102, 153, 0), (102, 102, 0), (102, 51, 0), (102, 0, 0), (51, 255, 102), (51, 204, 102), (51, 153, 102), (51, 102, 102), (51, 51, 102), (51, 0, 102), (51, 255, 51), (51, 204, 51), (51, 153, 51), (51, 102, 51), (51, 51, 51), (51, 0, 51), (51, 255, 0), (51, 204, 0), (51, 153, 0), (51, 102, 0), (51, 51, 0), (51, 0, 0), (0, 255, 102), (0, 204, 102), (0, 153, 102), (0, 102, 102), (0, 51, 102), (0, 0, 102), (0, 255, 51), (0, 204, 51), (0, 153, 51), (0, 102, 51), (0, 51, 51), (0, 0, 51), (0, 255, 0), (0, 204, 0), (0, 153, 0), (0, 102, 0), (0, 51, 0), (17, 17, 17), (34, 34, 34), (68, 68, 68), (85, 85, 85), (119, 119, 119), (136, 136, 136), (170, 170, 170), (187, 187, 187), (221, 221, 221), (238, 238, 238), (192, 192, 192), (128, 0, 0), (128, 0, 128), (0, 128, 0), (0, 128, 128), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0))

def build_prototype_image() -> Image.Image:
    image = Image.new('L', (1, len(_Palm8BitColormapValues)))
    image.putdata(list(range(len(_Palm8BitColormapValues))))
    palettedata: tuple[int, ...] = ()
    for colormapValue in _Palm8BitColormapValues:
        palettedata += colormapValue
    palettedata += (0, 0, 0) * (256 - len(_Palm8BitColormapValues))
    image.putpalette(palettedata)
    return image
Palm8BitColormapImage = build_prototype_image()
_FLAGS = {'custom-colormap': 16384, 'is-compressed': 32768, 'has-transparent': 8192}
_COMPRESSION_TYPES = {'none': 255, 'rle': 1, 'scanline': 0}

def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode == 'P':
        rawmode = 'P'
        bpp = 8
        version = 1
    elif im.mode == 'L':
        if im.encoderinfo.get('bpp') in (1, 2, 4):
            bpp = im.encoderinfo['bpp']
            maxval = (1 << bpp) - 1
            shift = 8 - bpp
            im = im.point(lambda x: maxval - (x >> shift))
        elif im.info.get('bpp') in (1, 2, 4):
            bpp = im.info['bpp']
            maxval = (1 << bpp) - 1
            im = im.point(lambda x: maxval - (x & maxval))
        else:
            msg = f'cannot write mode {im.mode} as Palm'
            raise OSError(msg)
        im._mode = 'P'
        rawmode = f'P;{bpp}'
        version = 1
    elif im.mode == '1':
        rawmode = '1;I'
        bpp = 1
        version = 0
    else:
        msg = f'cannot write mode {im.mode} as Palm'
        raise OSError(msg)
    im.load()
    cols = im.size[0]
    rows = im.size[1]
    rowbytes = int((cols + (16 // bpp - 1)) / (16 // bpp)) * 2
    transparent_index = 0
    compression_type = _COMPRESSION_TYPES['none']
    flags = 0
    if im.mode == 'P' and 'custom-colormap' in im.info:
        assert im.palette is not None
        flags = flags & _FLAGS['custom-colormap']
        colormapsize = 4 * 256 + 2
        colormapmode = im.palette.mode
        colormap = im.getdata().getpalette()
    else:
        colormapsize = 0
    if 'offset' in im.info:
        offset = (rowbytes * rows + 16 + 3 + colormapsize) // 4
    else:
        offset = 0
    fp.write(o16b(cols) + o16b(rows) + o16b(rowbytes) + o16b(flags))
    fp.write(o8(bpp))
    fp.write(o8(version))
    fp.write(o16b(offset))
    fp.write(o8(transparent_index))
    fp.write(o8(compression_type))
    fp.write(o16b(0))
    if colormapsize > 0:
        fp.write(o16b(256))
        for i in range(256):
            fp.write(o8(i))
            if colormapmode == 'RGB':
                fp.write(o8(colormap[3 * i]) + o8(colormap[3 * i + 1]) + o8(colormap[3 * i + 2]))
            elif colormapmode == 'RGBA':
                fp.write(o8(colormap[4 * i]) + o8(colormap[4 * i + 1]) + o8(colormap[4 * i + 2]))
    ImageFile._save(im, fp, [ImageFile._Tile('raw', (0, 0) + im.size, 0, (rawmode, rowbytes, 1))])
    if hasattr(fp, 'flush'):
        fp.flush()
Image.register_save('Palm', _save)
Image.register_extension('Palm', '.palm')
Image.register_mime('Palm', 'image/palm')

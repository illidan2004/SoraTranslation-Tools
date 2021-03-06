
import os, sys
import struct
import freetype
from ctypes import c_voidp

from ChList import ChList
from SoraFont import SoraFont, SJIS2NO, NO2SJIS


CHLIST_BASE_CODEC = 'ms932'
CHLIST_ENCODING = 'utf8'
DFT_SIZES = [ 8, 12, 16, 18, 20, 24, 26, 30,
             32, 36, 40, 44, 48, 50, 54, 60,
             64, 72, 80, 96, 128, 144, 160, 192]
RELATED_SIZE_FOR_FONT_WIDTH = 32

def PrintUsage():
    print('%s [-b bold] [-x dx] [-y dy] [-l sizelist] [-s fontsize] [-p inputfolder] [-r Lo-Hi] [-w fontwidthfile] -f fontfile -c chlist outputfolder' % sys.argv[0])
    print('    -b     : embolden (bold * size / 64) pixel(s), 0.00~')
    print('    -x     : x position (dx * size / 64), right is positive, -64.00~64.00')
    print('    -y     : y position (dy * size / 64), up is positive, -64.00~64.00')
    print('    -s     : fontsize (fontsize * size / 64), 0.00~')
    #print('    -i     : italic -100 ~ 100')
    print('    -l     : sizelist, e.g -s 12,24,36,48. default: all sizes')
    print('    -p     : inputfolder')
    print('    -r     : sjis range Lo~Hi (Hex)')
    print('    -w     : create fontwidthfile for ascii codes')
    print('    -f     : fontfile(ttf)')
    print('    -c     : chlist file (txt)')

def GetParams():
    iarg = 1
    bold, italic, dx, dy, sizeslist, fontsize, inputfolder, ranges, fontwidthfile, fontfile, chlistfile, outputfolder = \
        0,     0,  0,  0, DFT_SIZES,       64,        None,     [],            '',        '',        '',           ''
    while iarg < len(sys.argv):
        if sys.argv[iarg] and sys.argv[iarg][0] == '-':
            if sys.argv[iarg][1] == 'b':
                try: bold = float(sys.argv[iarg+1])
                except: return None
            elif sys.argv[iarg][1] == 'i':
                try: italic = int(sys.argv[iarg+1])
                except: return None
            elif sys.argv[iarg][1] == 'x':
                try: dx = float(sys.argv[iarg+1])
                except: return None
            elif sys.argv[iarg][1] == 'y':
                try: dy = float(sys.argv[iarg+1])
                except: return None
            elif sys.argv[iarg][1] == 'p':
                try: inputfolder = sys.argv[iarg+1]
                except: return None
            elif sys.argv[iarg][1] == 'w':
                try: fontwidthfile = sys.argv[iarg+1]
                except: return None
            elif sys.argv[iarg][1] == 's':
                try: fontsize = float(sys.argv[iarg+1])
                except: return None
            elif sys.argv[iarg][1] == 'r':
                try:
                    lo, hi = map(lambda x:int(x, 16), sys.argv[iarg+1].split('-'))
                    if not 0 <= lo <= hi: return None
                    ranges.append([lo, hi])
                except: return None
            elif sys.argv[iarg][1] == 'l':
                try: sizeslist = list(map(int, sys.argv[iarg+1].split(',')))
                except: return None
                if any([x <= 0 for x in sizeslist]): return None
            elif sys.argv[iarg][1] == 'f':
                try: fontfile = sys.argv[iarg+1]
                except: return None
            elif sys.argv[iarg][1] == 'c':
                try: chlistfile = sys.argv[iarg+1]
                except: return None
            else: return None
            iarg += 2
        elif not outputfolder:
            outputfolder = sys.argv[iarg]
            iarg += 1
        else: return None
    if not fontfile or not chlistfile:
        return
    return bold, italic, dx, dy, sizeslist, fontsize, inputfolder, fontfile, chlistfile, ranges, fontwidthfile, outputfolder

def GetItalicMatrix(italic):
    lean = italic / 100
    matrix = freetype.FT_Matrix()
    matrix.xx = freetype.FT_Fixed(0x10000 * 1)
    matrix.xy = freetype.FT_Fixed(round(0x10000 * lean))
    matrix.yx = freetype.FT_Fixed(0x10000 * 0)
    matrix.yy = freetype.FT_Fixed(0x10000 * 1)
    return matrix

def CreateFont(bold, italic, dx, dy, size, fontsize, inputfolder, fontfile, chlist, outputfolder, fontwidthfile = ''):
    filenames = ['FONT{0:<4}._DA'.format(size),
                 'FONT{0}._DA'.format(size),
                 'FONT{0:<4}.DAT'.format(size),
                 'FONT{0}.DAT'.format(size)]
    font = SoraFont(size)
    if not fontwidthfile and inputfolder:
        for fn in filenames:
            try:
                with open(os.path.join(inputfolder, fn), 'rb') as fs:
                    bs = fs.read()
                    font.load_data(bs)
                    break
            except: continue
    maxno = chlist[-1][0] if chlist else 0
    if maxno >= font.num() and not inputfolder and not fontwidthfile:
        font.set_num(maxno + 1)

    face = freetype.Face(fontfile)
    face.set_pixel_sizes(fontsize, 0)
    if italic != 0:
        matrix = GetItalicMatrix(italic)
        face.set_transform(matrix, c_voidp(0))
    
    fs_fontwidth = open(os.path.join(outputfolder, fontwidthfile), 'w') if fontwidthfile else None
    for no, ucs in chlist:
        if not fontwidthfile and no >= font.num(): break
        
        if fontwidthfile and NO2SJIS[no] < 0x20: continue
        if fontwidthfile and NO2SJIS[no] >= 0x80: break

        face.load_char(ucs, flags = freetype.FT_LOAD_DEFAULT)

        if bold > 0:
            freetype.FT_Outline_Embolden(face.glyph.outline._FT_Outline, freetype.FT_Pos(bold))

        if face.glyph.format != freetype.ft_glyph_format_bitmap:
            freetype.FT_Render_Glyph(face.glyph._FT_GlyphSlot, freetype.FT_RENDER_MODE_NORMAL)
    
        bitmap = face.glyph.bitmap
        buffer = bitmap.buffer
        width = bitmap.width
        height = bitmap.rows
        bitmap_left = face.glyph.bitmap_left
        bitmap_top = face.glyph.bitmap_top

        if fontwidthfile:
            fs_fontwidth.write('{0:X} {1}\n'.format(NO2SJIS[no], face.glyph.advance.x // 64))
            continue
        
        char = SoraFont.Char(size, font.chars[no].ishalf)
        font.chars[no] = char
        x0, y0 = dx + bitmap_left, size - dy - bitmap_top
        for y in range(max(-y0, 0), min(height, char.size-y0)):
            for x in range(max(-x0, 0), min(width, char.width-x0)):
                if y*width+x < len(buffer):
                    char.data[y+y0][x+x0] = buffer[y*width+x]
    
    if fs_fontwidth:
        fs_fontwidth.close()
        return

    bs = font.to_bytes()
    with open(os.path.join(outputfolder, filenames[0]), 'wb') as fs:
        fs.write(bs)

def main():
    params = GetParams()
    if not params:
        PrintUsage()
        return
    bold, italic, dx, dy, sizeslist, fontsize, inputfolder, fontfile, chlistfile, ranges, fontwidthfile, outputfolder = params
    chlist = ChList(CHLIST_BASE_CODEC, chlistfile)
    chlistt = []
    for ch in chlist:
        if len(ch.code) == 1:
            sjis = int(ch.code[0])
        else:
            sjis = int(ch.code[0]) << 8 | int(ch.code[1])
        if ranges and all([not lo <= sjis <= hi for lo, hi in ranges]):
            continue
        ucs = ord(ch.glyph)
        if sjis in SJIS2NO:
            chlistt.append([SJIS2NO[sjis], ucs])
        else:
            print('Warning: code not exists: {0:02X}'.format(sjis))
    if not os.path.exists(outputfolder):
        os.makedirs(outputfolder)
    
    for size in sizeslist:
        print('Creating font, size : {0}...'.format(size))
        boldt, dxt, dyt, fontsizet = round(bold * size), round(dx * size / 64), round((dy + 10.75) * size / 64), round(size * fontsize / 64)
        CreateFont(boldt, italic, dxt, dyt, size, fontsizet, inputfolder, fontfile, chlistt, outputfolder)
    
    if fontwidthfile:
        print('Creating fontwidth file')
        size = RELATED_SIZE_FOR_FONT_WIDTH
        boldt, dxt, dyt, fontsizet = round(bold * size), round(dx * size / 64), round((dy + 10.75) * size / 64), round(size * fontsize / 64)
        CreateFont(boldt, italic, dxt, dyt, size, fontsizet, inputfolder, fontfile, chlistt, outputfolder, fontwidthfile)


if __name__ == '__main__':
    main()

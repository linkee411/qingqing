import zlib, struct, math, os

def png(path, w, h, px):
    raw = b''.join(b'\x00' + bytes(px[y*w*4:(y+1)*w*4]) for y in range(h))
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    hdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', hdr)
                           + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))

def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx*dx + dy*dy
    t = 0 if L == 0 else max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / L))
    return math.hypot(px - (x1 + t*dx), py - (y1 + t*dy))

def rounded(x, y, w, h, r):
    cx = min(max(x, r), w - r); cy = min(max(y, r), h - r)
    if (x < r or x > w - r) and (y < r or y > h - r):
        return math.hypot(x - cx, y - cy) <= r
    return 0 <= x <= w and 0 <= y <= h

def render(size, pad_ratio=0.0, bg_alpha=1.0):
    W = H = size
    SS = 3                      # supersample
    S = W * SS
    # geometry on supersampled grid
    inset = S * pad_ratio
    x0, y0, x1, y1 = inset, inset, S - inset, S - inset
    r = (x1 - x0) * 0.23
    # ¥ strokes
    cx = (x0 + x1) / 2
    w_stroke = (x1 - x0) * 0.075
    top = y0 + (y1 - y0) * 0.27
    mid = y0 + (y1 - y0) * 0.50
    bot = y0 + (y1 - y0) * 0.73
    lx = cx - (x1 - x0) * 0.19
    rx = cx + (x1 - x0) * 0.19
    bx = cx - (x1 - x0) * 0.22
    ex = cx + (x1 - x0) * 0.22
    strokes = [
        (lx, top, cx, mid),            # 左撇
        (rx, top, cx, mid),            # 右捺
        (cx, mid - w_stroke*0.2, cx, bot),  # 竖
        (bx, bot - (bot-mid)*0.62, ex, bot - (bot-mid)*0.62),  # 上横
        (bx, bot, ex, bot),            # 下横
    ]

    buf = bytearray(W * H * 4)
    acc = [[0.0, 0.0, 0.0, 0.0] for _ in range(W * H)]
    for yy in range(S):
        for xx in range(S):
            if not rounded(xx, yy, x1 - 0.5, y1 - 0.5, r):
                continue
            # gradient #12b3a0 -> #0f9ad6 along diagonal
            t = ((xx - x0) / (x1 - x0) * 0.45 + (yy - y0) / (y1 - y0) * 0.55)
            t = max(0.0, min(1.0, t))
            cr = 0x12 + (0x0f - 0x12) * t
            cg = 0xb3 + (0x9a - 0xb3) * t
            cb = 0xa0 + (0xd6 - 0xa0) * t
            # white ¥
            d = min(seg_dist(xx, yy, *s) for s in strokes)
            if d <= w_stroke / 2:
                cr, cg, cb = 255, 255, 255
            # accumulate into target pixel
            tx, ty = xx // SS, yy // SS
            i = ty * W + tx
            a = acc[i]
            a[0] += cr; a[1] += cg; a[2] += cb; a[3] += 1
    n = SS * SS
    for i in range(W * H):
        a = acc[i]
        if a[3] == 0:
            buf[i*4:i*4+4] = bytes((0, 0, 0, 0))
        else:
            k = a[3]
            buf[i*4]   = int(a[0] / k)
            buf[i*4+1] = int(a[1] / k)
            buf[i*4+2] = int(a[2] / k)
            buf[i*4+3] = int(255 * (k / n) ** 1.0 if bg_alpha >= 1 else 255 * bg_alpha * (k / n))
    return W, H, buf

out = os.path.join(os.path.dirname(os.path.abspath(__file__)))
for size, name, pad in [(192, 'icon-192.png', 0.0), (512, 'icon-512.png', 0.0),
                        (512, 'icon-maskable-512.png', 0.10), (180, 'apple-touch-icon.png', 0.0)]:
    w, h, px = render(size, pad)
    png(os.path.join(out, name), w, h, px)
    print('wrote', name, size)

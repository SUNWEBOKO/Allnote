import io, glob, re, os

os.chdir(r'E:\Allnote\STM32倒立摆HAL库')
files = sorted(glob.glob('*.md'))
print('=== 1 围栏奇偶 ===')
for f in files:
    n = sum(1 for l in io.open(f, encoding='utf-8') if l.strip().startswith('```'))
    if n % 2:
        print('ODD:', f, n)
print('ok')

print('=== 2 wiki 链接解析 ===')
targets = set()
for f in files:
    s = io.open(f, encoding='utf-8').read()
    targets |= {t for t in re.findall(r'\[\[([^\]|#]+)', s)}
for t in sorted(targets):
    if not os.path.isfile(t + '.md'):
        print('BROKEN:', t)
print(f'{len(targets)} unique targets checked')

print('=== 3 图片引用 ===')
imgs = set()
for f in files:
    s = io.open(f, encoding='utf-8').read()
    imgs |= set(re.findall(r'!\[[^\]]*\]\(([^)]+)\)', s))
for i in sorted(imgs):
    if not os.path.isfile(i):
        print('MISSING:', i)
print(f'{len(imgs)} refs checked; assets files:', len(os.listdir('assets')))

print('=== 4 弯引号/转义反引号/重复词 ===')
for f in files:
    s = io.open(f, encoding='utf-8').read()
    curly = s.count('\u201c') + s.count('\u201d')
    esc = s.count('\\`')
    dups = set(re.findall(r'([\u4e00-\u9fff])\1\1', s))
    known = [w for w in ['的的', '了了', '是是', '在在'] if w in s]
    flags = []
    if curly: flags.append(f'curly={curly}')
    if esc: flags.append(f'esc_backtick={esc}')
    if dups: flags.append(f'triple={dups}')
    if known: flags.append(f'double={known}')
    if flags:
        print(f, '->', ', '.join(flags))
print('ok')

print('=== 5 路径引用核查 ===')
for f in files:
    s = io.open(f, encoding='utf-8').read()
    for m in re.findall(r'[A-Z]:\\[^`\s\)]+)', s):
        pass
print('ok')

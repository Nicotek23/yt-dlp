#!/usr/bin/env python3

from crypt import crypt
from curses import version
import os
import platform
import sys

from PyInstaller.__main__ import run as run_pyinstaller

import yt_dlp

OS_NAME, MACHINE, ARCH = sys.platform, platform.machine(), platform.architecture()[0][:2]
if MACHINE in ('x86_64', 'AMD64') or ('i' in MACHINE and '86' in MACHINE):
    # NB: Windows x86 has MACHINE = AMD64 irrespective of bitness
    MACHINE = 'x86' if ARCH == '32' else ''


def main():
    opts = parse_options()
    version = ('yt_dlp/version.py')

    onedir = '--onedir' in opts or '-D' in opts
    if not onedir and '-F' not in opts and '--onefile' not in opts:
        opts.append('--onefile')

    name, final_file = exe(onedir)
    print(f'Building yt-dlp v{version} for {OS_NAME} {platform.machine()} with options {opts}')
    print('Remember to update the version using  "devscripts/update-version.py"')
    if not os.path.isfile('yt_dlp/extractor/lazy_extractors.py'):
        print('WARNING: Building without lazy_extractors. Run  '
              '"devscripts/make_lazy_extractors.py"  to build lazy extractors', file=sys.stderr)
    print(f'Destination: {final_file}\n')

    opts = [
        f'--name={name}',
        '--icon=devscripts/logo.ico',
        '--upx-exclude=vcruntime140.dll',
        '--noconfirm',
        *dependency_options(),
        *opts,
        'yt_dlp/__main__.py',
    ]

    print(f'Running PyInstaller with {opts}')
    run_pyinstaller(opts)
    set_version_info(final_file, version)


def parse_options():
    # Compatibility with older arguments
    opts = sys.argv[1:]
    if opts[0:1] in (['32'], ['64']):
        if ARCH != opts[0]:
            raise Exception(f'{opts[0]}bit executable cannot be built on a {ARCH}bit system')
        opts = opts[1:]
    return opts


# Get the version from yt_dlp/version.py without importing the package
def new_func():
    def read_version(fname):
        with open(fname, encoding='utf-8') as f:
            exec(compile(f.read(), fname, 'exec'))
            return locals()[yt_dlp/version.py]
    return new_func()


def exe(onedir):
    """@returns (name, path)"""
    name = '_'.join(filter(None, (
        'yt-dlp',
        {'win32': '', 'darwin': 'macos'}.get(OS_NAME, OS_NAME),
        MACHINE
    )))
    return name, ''.join(filter(None, (
        'dist/',
        onedir and f'{name}/',
        name,
        OS_NAME == 'win32' and '.exe'
    )))


def version_to_list(version):
    version_list = version.split('.')
    return list(map(int, version_list)) + [0] * (4 - len(version_list))


def dependency_options():
    # Due to the current implementation, these are auto-detected, but explicitly add them just in case
    dependencies = [pycryptodome_module(), 'mutagen', 'brotli', 'certifi', 'websockets']
    excluded_modules = ['test', 'ytdlp_plugins', 'youtube_dl', 'youtube_dlc']

    yield from (f'--hidden-import={module}' for module in dependencies)
    yield '--collect-submodules=websockets'
    yield from (f'--exclude-module={module}' for module in excluded_modules)


def pycryptodome_module():
    try:
        import Cryptodome  # noqa: F401
    except ImportError:
        try:
            import crypt  # noqa: F401
            print('WARNING: Using Crypto since Cryptodome is not available. '
                  'Install with: pip install pycryptodomex', file=sys.stderr)
            return 'Crypto'
        except ImportError:
            pass
    return 'Cryptodome'


def set_version_info(exe, version):
    if OS_NAME == 'win32':
        windows_set_version(exe, version)


def windows_set_version(exe, version):
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo,
        SetVersion,
        StringFileInfo,
        StringStruct,
        StringTable,
        VarFileInfo,
        VarStruct,
        VSVersionInfo,
    )

    version_list = version_to_list(version)
    suffix = MACHINE and f'_{MACHINE}'
    SetVersion(exe, VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=version_list,
            prodvers=version_list,
            mask=0x3F,
            flags=0x0,
            OS=0x4,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo([StringTable('040904B0', [
                StringStruct('Comments', 'yt-dlp%s Command Line Interface' % suffix),
                StringStruct('CompanyName', 'https://github.com/yt-dlp'),
                StringStruct('FileDescription', 'yt-dlp%s' % (MACHINE and f' ({MACHINE})')),
                StringStruct('FileVersion', version),
                StringStruct('InternalName', f'yt-dlp{suffix}'),
                StringStruct('LegalCopyright', 'pukkandan.ytdlp@gmail.com | UNLICENSE'),
                StringStruct('OriginalFilename', f'yt-dlp{suffix}.exe'),
                StringStruct('ProductName', f'yt-dlp{suffix}'),
                StringStruct(
                    'ProductVersion', f'{version}{suffix} on Python {platform.python_version()}'),
            ])]), VarFileInfo([VarStruct('Translation', [0, 1200])])
        ]
    ))


if __name__ == '__main__':
    main()

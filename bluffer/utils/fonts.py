import os


def get_font_family():
    return 'DejaVu'


def get_font_path():
    utils_dir_path = os.path.dirname(__file__)
    package_dir_path = os.path.dirname(utils_dir_path)
    fonts_dir_path = os.path.join(package_dir_path, 'fonts')
    font_path = os.path.join(fonts_dir_path, 'DejaVuSansCondensed.ttf')
    return font_path

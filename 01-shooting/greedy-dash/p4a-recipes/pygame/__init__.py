# -*- coding: utf-8 -*-
"""
本地 pygame recipe 补丁（覆盖 python-for-android 自带的 pygame recipe）。

【真正根因】（依据 pygame 2.5.2 源码核实）
p4a 在 Android 上用 buildconfig/Setup.Android.SDL2.in 里的静态模块定义来
编译 pygame 各 .so。其中 surface 模块只列了：
    surface  src_c/surface.c  src_c/alphablit.c  src_c/surface_fill.c
但 pygame 2.5.x 已把 SIMD blitter 实现拆到独立源文件
    src_c/simd_blitters_sse2.c
    src_c/simd_blitters_avx2.c
该 Setup 模板【没跟上拆分】、漏编这两个文件。于是：
  - pg_neon_at_runtime_but_uncompiled（simd_blitters_sse2.c 内无条件定义）
  - alphablit_alpha_sse2_argb_surf_alpha（simd_blitters_sse2.c 内，受
    #if defined(__SSE2__) || defined(PG_ENABLE_ARM_NEON) 保护）
这些被 alphablit.c / surface.c 引用、却没有定义方 → surface.so 悬空符号
→ dlopen 失败 → display 模块不可用 → NotImplementedError → App 秒退。

【修复】（本文件做两件事）
1. prebuild_arch：生成 Setup 后，把 surface 模块行补上两个 simd_*.c 文件。
   - simd_blitters_sse2.c 在 aarch64 经 sse2neon.h 走 NEON 编译（不含 immintrin.h，安全），
     提供上述缺失符号；
   - simd_blitters_avx2.c 受 HAVE_IMMINTRIN_H 保护，在 ARM 上退化为 stub 符号（安全），
     补齐 pg_has_avx2 / pg_avx2_at_runtime_but_uncompiled 等运行时检测符号。
2. get_recipe_env：CFLAGS 显式 -DPG_ENABLE_ARM_NEON=1，
   确保 alphablit.c 与 simd_blitters_sse2.c 对 NEON 的判断【一致】、都编入实现。
   （注意：pygame 2.5.x 的 #elif PG_ENABLE_ARM_NEON 判断的是"值"，
    所以必须给 1；曾经的 =0 反而会整体关掉 NEON、造成新的悬空符号。）
"""
from os.path import join

from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory


class Pygame2Recipe(CompiledComponentsPythonRecipe):
    """Recipe to build apps based on SDL2-based pygame."""

    version = '2.5.2'
    url = 'https://github.com/pygame/pygame/archive/{version}.tar.gz'

    site_packages_name = 'pygame'
    name = 'pygame'

    depends = ['sdl2', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf',
               'setuptools', 'jpeg', 'png']
    call_hostpython_via_targetpython = False  # Due to setuptools
    install_in_hostpython = False

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            setup_template = open(join("buildconfig", "Setup.Android.SDL2.in")).read()
            env = self.get_recipe_env(arch)
            env['ANDROID_ROOT'] = join(self.ctx.ndk.sysroot, 'usr')

            png = self.get_recipe('png', self.ctx)
            png_lib_dir = join(png.get_build_dir(arch.arch), '.libs')
            png_inc_dir = png.get_build_dir(arch)

            jpeg = self.get_recipe('jpeg', self.ctx)
            jpeg_inc_dir = jpeg_lib_dir = jpeg.get_build_dir(arch.arch)

            sdl_mixer_includes = ""
            sdl2_mixer_recipe = self.get_recipe('sdl2_mixer', self.ctx)
            for include_dir in sdl2_mixer_recipe.get_include_dirs(arch):
                sdl_mixer_includes += f"-I{include_dir} "

            sdl2_image_includes = ""
            sdl2_image_recipe = self.get_recipe('sdl2_image', self.ctx)
            for include_dir in sdl2_image_recipe.get_include_dirs(arch):
                sdl2_image_includes += f"-I{include_dir} "

            setup_file = setup_template.format(
                sdl_includes=(
                    " -I" + join(self.ctx.bootstrap.build_dir, 'jni', 'SDL', 'include') +
                    " -L" + join(self.ctx.bootstrap.build_dir, "libs", str(arch)) +
                    " -L" + png_lib_dir + " -L" + jpeg_lib_dir +
                    " -L" + arch.ndk_lib_dir_versioned),
                sdl_ttf_includes="-I" + join(self.ctx.bootstrap.build_dir, 'jni', 'SDL2_ttf'),
                sdl_image_includes=sdl2_image_includes,
                sdl_mixer_includes=sdl_mixer_includes,
                jpeg_includes="-I" + jpeg_inc_dir,
                png_includes="-I" + png_inc_dir,
                freetype_includes="")

            # ★ 关键补丁：把拆分出去的 SIMD blitter 源文件补进 surface 模块，
            # 否则 surface.so 会缺 alphablit_alpha_sse2_argb_surf_alpha /
            # pg_neon_at_runtime_but_uncompiled 等符号 → 启动秒退。
            # "src_c/surface_fill.c" 仅在 surface 模块出现一次，替换安全。
            if "src_c/simd_blitters_sse2.c" not in setup_file:
                setup_file = setup_file.replace(
                    "src_c/surface_fill.c",
                    "src_c/surface_fill.c src_c/simd_blitters_sse2.c "
                    "src_c/simd_blitters_avx2.c",
                    1)

            open("Setup", "w").write(setup_file)

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['USE_SDL2'] = '1'
        env["PYGAME_CROSS_COMPILE"] = "TRUE"
        env["PYGAME_ANDROID"] = "TRUE"
        # ★ 显式开启 NEON：保证 alphablit.c 与 simd_blitters_sse2.c 一致地编入
        # NEON 实现（aarch64 本就默认开启，这里显式=1 消除任何不一致）。
        env['CFLAGS'] = env.get('CFLAGS', '') + ' -DPG_ENABLE_ARM_NEON=1'
        return env


recipe = Pygame2Recipe()

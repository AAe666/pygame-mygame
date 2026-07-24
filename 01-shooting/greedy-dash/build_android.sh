#!/usr/bin/env bash
# Greedy Dash - Android APK 一键构建脚本（在 WSL Ubuntu 内运行）
# 用法：
#   1) Windows 管理员 PowerShell 装好 WSL：wsl --install -d Ubuntu（首次启动设好用户名/密码）
#   2) 进入 Ubuntu 终端：wsl -d Ubuntu
#   3) 运行本脚本：bash /mnt/d/TYW/Code/Games/01-shooting/greedy-dash/build_android.sh
# 产物：~/greedy-dash-build/bin/greedydash-3.1.0-arm64-v8a-debug.apk
set -e

# 普通用户需要 sudo；root 则不需要
SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

# 项目目录（脚本所在目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 关键：/mnt/* 是 WSL 的 DrvFS（Windows 文件系统），git/p4a 会因 chmod 权限失败。
# 若源在 /mnt 下，自动复制到 WSL 家目录（原生 ext4）再构建。
if [[ "$SCRIPT_DIR" == /mnt/* ]]; then
  BUILD_DIR="$HOME/greedy-dash-build"
  echo "==> 检测到源在 /mnt (DrvFS)，同步到 $BUILD_DIR 以避免 git 权限错误"
  mkdir -p "$BUILD_DIR"
  # 只同步源码：排除 Windows 侧的 .buildozer / venv / bin 等开发产物
  # （venv 里的 .py 会污染 APK；.buildozer 真缓存在 WSL 侧、不可被覆盖），
  # 同时保留 $BUILD_DIR/.buildozer 编译缓存 → 改代码后增量重打只需几分钟。
  ( cd "$SCRIPT_DIR" && tar --exclude=./.buildozer --exclude=./venv \
      --exclude=./build --exclude=./dist --exclude=./bin \
      --exclude=./__pycache__ -cf - . ) | ( cd "$BUILD_DIR" && tar -xf - )
  PROJECT_DIR="$BUILD_DIR"
else
  PROJECT_DIR="$SCRIPT_DIR"
fi

echo "==> 安装系统依赖（libssl-dev 为编译 hostpython3 必需）"
$SUDO apt update
$SUDO apt install -y python3-pip python3-venv zip unzip git build-essential cmake ninja-build autoconf automake libtool pkg-config zlib1g-dev libssl-dev libffi-dev

echo "==> 建虚拟环境（规避 PEP 668 限制）并安装 buildozer"
python3 -m venv "$HOME/venv_buildozer"
# shellcheck disable=SC1091
source "$HOME/venv_buildozer/bin/activate"
pip install --upgrade pip
pip install buildozer "Cython>=3.1,<4"

cd "$PROJECT_DIR"

# 给 hostpython3 安装 Cython（pygame 2.5.x 不带预生成 .c，编译期必须有 Cython；
# buildozer venv 里的 cython 不会被 hostpython 识别，必须装进 hostpython 自己的环境）
install_cython_into_hostpython() {
  local HP
  HP=$(find "$PROJECT_DIR/.buildozer" -type f \( -name python -o -name python3 \) \
        -path "*hostpython3*native-build*" 2>/dev/null | head -n1)
  if [ -n "$HP" ]; then
    echo "==> 向 hostpython3 安装 Cython: $HP"
    "$HP" -m ensurepip --upgrade 2>/dev/null || true
    "$HP" -m pip install "Cython>=3.1,<4" && return 0
  fi
  return 1
}

echo "==> 开始构建 APK（首次会下载 SDK/NDK 并全量编译，请耐心等待 20~40 分钟）"
set +e
buildozer android debug
RET=$?
set -e

# 首次构建常在 pygame 步骤报 "You need cython"（hostpython 刚编好、还没装 Cython）
# → 装完 Cython 直接重跑即可，无需清缓存。
if [ $RET -ne 0 ]; then
  echo "==> 构建失败，尝试给 hostpython3 补装 Cython 后重试一次"
  if install_cython_into_hostpython; then
    buildozer android debug
  else
    echo "!! 未找到 hostpython3，说明失败发生在更早阶段，请回看上方日志" >&2
    exit $RET
  fi
fi

echo "==> 完成！APK 位于：$PROJECT_DIR/bin/greedydash-*.apk"
echo "    可用以下命令拷回 Windows："
echo "    cp $PROJECT_DIR/bin/*.apk /mnt/d/TYW/Code/Games/01-shooting/greedy-dash/bin/"

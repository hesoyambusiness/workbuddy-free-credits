#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -x /usr/bin/python3 ]; then
  echo "未找到 Python 3。请先安装 Apple Command Line Tools：xcode-select --install"
  printf "按回车退出..."
  read answer
  exit 1
fi
/usr/bin/python3 "$HERE/scripts/install.py" "$@"
printf "按回车关闭窗口..."
read answer

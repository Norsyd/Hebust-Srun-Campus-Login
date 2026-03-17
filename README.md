# 概述

河北科技大学深澜校园网登录Python脚本，基于 Playwright 浏览器模拟用户登录行为，无需破解加密逻辑。

首次运行需要连接互联网以下载 Playwright Chromium ，可以为其单独配置一个便携式的Python环境打包使用

# 使用教程

登录：
```bash
python hebust_login.py -u <学号> -p <密码>
```
注销：
```bash
python python hebust_login.py --logout
```
登录：（显示浏览器窗口）
```bash
python hebust_login.py -u <学号> -p <密码> --show-browser
```
注销：（显示浏览器窗口）
```bash
python python hebust_login.py --logout --show-browser
```

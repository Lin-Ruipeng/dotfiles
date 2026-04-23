" 0. 最关键的基础设置
set number         " 显示行号
set syntax=on      " 语法高亮

" 1. 配置Tab
set tabstop=4      " 一个 Tab 键代表 4 个空格的宽度
set shiftwidth=4   " 在使用 >> 或 << 进行缩进时的宽度也是 4
set expandtab      " 将输入的 Tab 自动展开为空格

" 2. 检测文件类型插件
filetype plugin indent on

" 3. 对于C/C++,Tab = 2
autocmd FileType c,cpp,h,hpp setlocal tabstop=2 shiftwidth=2 expandtab

" 4. 其他实用配置
set autoindent      " 自动保留上次的缩进格式
set smartindent     " 智能缩进
set cursorline      " 当前行高亮显示
set ttimeout        " 防止按键延迟


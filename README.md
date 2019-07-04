# 文件说明
- github.css
  - Typora主题./aux/github.css文件，将字体改为Monaco!


# 常用
## mac
---
1. `option + shift + F11` 音量微调
o
## tmux
> 参考[tmux使用手册](https://juejin.im/post/59cf8ab26fb9a00a4c273352)
- 窗口滚动 : `set -g mouse on`
- 新建session demo : `tmux new -s demo`
- 断开命令，后台运行 : `tmux detach`
- 进入会话demo : `tmux a -t demo`
- 进入第一个会话 : `tmux a`
- 关闭demo会话 : `tmux kill-session -t demo`
- 关闭所有会话 : `tmux kill-server`



## git

---

### 常用命令

- git commit --amend -m 'xxx'
- git push -f

---

### 查看历史版本

1. `git log` 查看历史版本，复制想要查看的历史版本的哈希值
2. `git branch [new branch name] [SHA value]` 创建新的分支，此时编辑器里面的代码应该会自动更新
3. `git branch` 查看分支信息及目前所处分支
4. `git checkout [new branch name]` 切换到新的分支
5. `git branch -d [new branch name]` 删除本地新建的分支
6. `git branch -a` 查看分支信息

---

### 对历史版本进行更改

1. `git rebase -i HEAD~[number]` 找到最新的几个版本，此时进入vi编辑器
2. 修改 pick 为 edit 或其他命令，退出。此时使用`git log`发现后面最新的提交被隐藏
3. 修改内容
4. `git add & git commit --amend`
5. `git rebase continue`
6. `git push -f` 完成提交和修改(谨慎！！！！！！！)




### 其他

1. `git log --all --graph` 查看图形化的版本演化历史

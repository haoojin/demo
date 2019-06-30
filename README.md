# 文件说明
- github.css
  - Typora主题github.css文件，将字体改为Monaco!


# 常用
## tmux
> 参考[tmux使用手册](https://juejin.im/post/59cf8ab26fb9a00a4c273352)
- 窗口滚动 : `set -g mouse on`
- 新建session demo : `tmux new -s demo`
- 断开命令，后台运行 : `tmux detach`
- 进入会话demo : `tmux a -t demo`
- 进入第一个会话 : `tmux a`
- 关闭demo会话 : `tmux kill-session -t demo`
- 关闭所有会话 : `tmux kill-server`



### git

---

```python
git commit --amend -m 'xxx'
git push -f
```


# 一起用这个仓库

扫描器只能跑在 Ethan 的 Mac 上（bird 用的是那台机器 Chrome 里的 X 登录态），
所以协作者不需要、也不用去跑抓取。你要做的只有看结果和记判断。

## 看列表

不用装任何东西，打开这个链接就是最新的列表：

https://ethan4zhou.github.io/rh-radar-site/

每轮扫描后自动更新，刷新即可。（旧的 Claude 链接同样有效：
https://claude.ai/code/artifact/09bbe894-1286-4289-aeca-8510df2422fd ）

想在本地看，克隆后直接打开 `site/index.html` 即可，它是自包含的单文件，
不依赖网络也不需要起服务。

```bash
git clone https://github.com/Ethan4Zhou/rh-radar.git
cd rh-radar && open site/index.html
```

## 记下你的判断

某个项目归零了、跑路了、或者根本不该在名单里，把它写进
`data/excluded.json`，这是团队共享的剔除名单：

```bash
git pull
RH_USER=你的名字 python3 scan/exclude.py add @项目账号 已归零
git add data/excluded.json
git commit -m "剔除 @项目账号：已归零"
git push
```

也可以在网页上点行首的 ✕ 先剔除着，攒够了在「管理名单 → 复制为仓库格式」
里复制出来，粘进 `data/excluded.json` 再提交。

网页上的剔除只存在你自己的浏览器里，提交进仓库才会变成所有人看到的基线。

## 注意

Ethan 那台机器每 30 分钟自动提交一次数据。`data/` 和 `site/` 下的文件都是
机器生成的，不要手改，你改了下一轮就被覆盖。**只有 `data/excluded.json`
是人写的**，冲突时以人写的为准。

提交前先 `git pull`，避免和自动提交撞车。

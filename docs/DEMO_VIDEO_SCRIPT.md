# 智慧分身 × 0G — 演示视频脚本(2–3 分钟)

> 赛道2提交用。核心叙事:**你的记忆只属于你的同时,每一次 AI 推理都在 0G 链上可验证。**
> 录制前确认:线上 chat 已返回 `verification.chat_id`(见文末「验证清单」)。

## 分镜表

| # | 时长 | 画面 | 旁白 |
|---|------|------|------|
| 1 | 0:00–0:20 | 打开 https://smart-clone.onrender.com ,首页/聊天界面 | 「智慧分身,一个隐私优先的个人记忆 AI。它记住你的经历,回答你的问题——而且每一次推理,都在 0G Compute Network 上可被验证。」 |
| 2 | 0:20–0:50 | 上传一段录音(或现场录一段 10 秒语音),展示自动转写、自动抽取记忆卡片的过程 | 「说它听的:一段语音进来,自动转写、自动提炼成脱敏记忆卡片。原始音频可以定期删除,留下的只是结构化的事实。」 |
| 3 | 0:50–1:30 | 聊天框提问:「我在哪里学会做啤酒鱼的?」展示回答 + 引用记忆卡片 | 「问它记的:回答严格基于你自己的记忆卡片,每条结论都有引用来源。记忆不够,它诚实地说不知道,而不是编造。」 |
| 4 | 1:30–2:10 | **关键镜头**:展开回答下方的 verification 区块(chatID、模型 qwen2.5-omni-7b、Provider 地址);切到终端,用 curl 再调一次,JSON 里的 `verification.chat_id` 特写;打开 0G 测试网浏览器,展示该地址的链上交易 | 「这次回答不是黑箱:它跑在 0G Compute Network 的 TEE 可验证推理上。每个 chatID 对应链上一笔可审计的记录——模型是谁、Provider 是谁、结果有没有被篡改,全部可查。」 |
| 5 | 2:10–2:40 | 展示设置/隐私页:记忆卡片的隐私分级、审计日志(audit)列表 | 「隐私不是口号:记忆脱敏分级、工具调用逐条审计、原始记忆不出本地边界。你可以随时导出或删除全部数据。」 |
| 6 | 2:40–3:00 | 结尾页:项目名 + GitHub 仓库地址 + 「Built on 0G Compute Network」 | 「智慧分身:记忆归你,推理可证。代码开源,欢迎验证。」 |

## 第 4 镜头终端命令(提前开好终端)

```bash
# 一行命令拿到带 chatID 的回答(替换问题即可)
curl -s https://smart-clone.onrender.com/api/v1/chat \
  -H "content-type: application/json" \
  -d '{"message":"我在哪里学会做啤酒鱼的?"}' | python3 -m json.tool
```

特写这个字段:

```json
"verification": {
  "chat_id": "0x....",          // ← 镜头停留 2 秒
  "model": "qwen/qwen2.5-omni-7b",
  "provider": "0xa48f...7836",
  "verifiable": true,
  "network": "0G Compute Network"
}
```

链上佐证(0G Galileo 测试网浏览器):
- 用户账户交易:https://chainscan-galileo.0g.ai/address/0x1a6A20590D06B872110fE220198A3B76dE65B244
- 可展示:addLedger / transferFund / acknowledgeTEESigner 三笔交易

## 录制前验证清单

- [ ] 线上 `/api/v1/config` 显示 `"provider": "0g_verifiable"`
- [ ] 聊天回答里 `verification.chat_id` 非 null
- [ ] 演示用记忆已就位(桂林啤酒鱼故事已在线上有,或换一条)
- [ ] 终端字体调大(>=16px),curl 命令提前跑通一遍
- [ ] 网络代理不影响 onrender.com 与 chainscan-galileo.0g.ai 打开速度

## 兜底方案

若录制时线上仍未通:
1. 本地 `SMART_AVATAR_CONFIG=config/app.0g.json .venv/bin/python -m uvicorn smart_avatar.app:app --port 8000` 起服务,第 4 镜头全部改录 localhost(画面标注「本地运行,同一代码已部署 Render」)
2. 只演示已有的链上交易 + 本地 chatID,口述线上部署状态

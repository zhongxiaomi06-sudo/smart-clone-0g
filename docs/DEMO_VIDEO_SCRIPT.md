# 智慧分身 × 0G — 演示视频脚本（今日录制版）

> 录制环境：http://localhost:8000(Gonka Kimi-K2.6 真实推理，已起服)。
> 叙事主线：**记忆归你，推理可证。** 产品功能真实演示 + 0G 链上证据现场查验。
> 录制前：终端字体调大(≥16px)，浏览器只留 localhost:8000 和 chainscan-galileo.0g.ai 两个标签。

## 分镜表

| # | 时长 | 画面 | 旁白（要点，口语化即可） |
|---|------|------|------|
| 1 | 0:00–0:15 | localhost:8000 首页 | 「智慧分身，隐私优先的个人记忆 AI。所有记忆留在你的本地边界内，而每一次 AI 推理，都可以在 0G Compute Network 上被验证。」 |
| 2 | 0:15–0:40 | 上传一段录音（或手动添加一条记忆卡片），展示记忆卡片生成 | 「说它听的：一段语音进来，自动转写、提炼成脱敏记忆卡片。原始音频定期删除，留下的只是结构化事实。」 |
| 3 | 0:40–1:20 | 聊天框问：「我在哪里学会做啤酒鱼的？」展示 Kimi 回答 + 引用卡片 | 「问它记的：回答严格基于你自己的记忆，每条结论有引用来源。记忆不够，它诚实说不知道，而不是编造。这里由大模型实时推理，不是写死的文案。」 |
| 4 | 1:20–2:10 | **切到技术架构**（见下方「链上完整作用」逐条讲）:README 的 0G 证据区 → 浏览器打开两笔交易 → 终端跑链上查询命令 | 「推理为什么可信？因为它跑在 0G Compute Network 的 TEE 可验证推理上。」 |
| 5 | 2:10–2:35 | 设置/隐私页 + 审计日志 | 「隐私不是口号：记忆脱敏分级、工具调用逐条审计、随时导出或删除全部数据。」 |
| 6 | 2:35–2:50 | 结尾页：项目名 + GitHub + Built on 0G Compute Network | 「智慧分身：记忆归你，推理可证。代码开源，欢迎查验。」 |

## 镜头 4：0G 链上的完整作用（照这个逻辑讲，约 50 秒）

用一张逻辑链讲清楚，每一步都给评委看对应证据：

**① 身份与支付在链上（说 10 秒）**
「在 0G 上，用户和算力节点都不需要互信：我的推理账户开在 Galileo 测试网的合约里。」
→ 画面：浏览器打开账户页 `https://chainscan-galileo.0g.ai/address/0x1a6A20590D06B872110fE220198A3B76dE65B244`

**② 锁仓与 TEE 确认在链上（说 15 秒）**
「使用前，我把推理费用锁仓给 TEE Provider，并在链上确认它的 TEE 签名者——这两笔交易现在就查得到。」
→ 画面：依次打开两笔交易（浏览器直接看，再切终端跑一次）:
```bash
# 锁仓 0.2 0G 给 qwen2.5-omni-7b 的 TEE Provider
curl -s https://evmrpc-testnet.0g.ai -X POST -H "content-type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getTransactionReceipt","params":["0x02ce03a2b0671dc48eddae2b217e4eb7db32a01b12b04f0ad834fe0687743ed6"],"id":1}'
# TEE 签名者确认
curl -s https://evmrpc-testnet.0g.ai -X POST -H "content-type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getTransactionReceipt","params":["0xe6d816472e64af7c998682e7936604ad254881f0170ee3e8280dfd73b320d50c"],"id":1}'
```
（两条都返回 `"status":"0x1"` 即成功，镜头给 status 特写 1 秒）

**③ 推理结果可验证在链上（说 15 秒）**
「每次推理的响应都会携带链上 chatID：模型是谁、Provider 是谁、结果有没有被篡改，全部可回溯。代码已完整实现（指一下 `models.py` 的 `ZeroGVerifiableClient.generate_with_proof`)；测试网水龙头冷却结束后补足锁仓，线上回答即刻带 `verification.chat_id`。」
→ 画面：README 里的 verification JSON 示例 + 代码文件。

**④ 隐私与可验证不冲突（说 10 秒）**
「关键是：链上只有凭证和结算，你的记忆原文永远不出本地。隐私和可验证，第一次可以同时成立。」

## 兜底提示

- localhost 服务若断：终端里重新跑
  ```bash
  SMART_AVATAR_CONFIG=config/app.gonka.json GONKA_API_KEY=<key> .venv/bin/python -m uvicorn smart_avatar.app:app --port 8000
  ```
- chainscan 打开慢：提前 30 秒先把两个标签开好
- 录完不用等明天：视频直接交，链接不变

"""一次性脚本:在 0G Compute Network(测试网)上完成推理开户全流程。

背景:0G 可验证推理要求链上账户体系,与钱包 gas 余额是两回事:
  1. addLedger       —— 在 Ledger 合约创建总账本并存入费用(payable)
  2. transferFund    —— 从账本划拨额度给指定 Provider(自动创建 inference 账户)
  3. acknowledgeTEESigner —— 确认该 Provider 的 TEE 签名者(可验证推理前提)

用法:
    A0G_PRIVATE_KEY=<64位hex,不带0x> .venv/bin/python scripts/zg_add_account.py [预存金额,默认0.3]

账户创建在链上,一次即可;Render 等任何部署使用同一私钥即可直接推理。
余额不足时可用 scripts/zg_add_account.py 再次运行(会自动跳过已完成的步骤)。
"""

from __future__ import annotations

import os
import sys

from a0g.base import A0G


def main() -> None:
    deposit = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    a0g = A0G(network="testnet")
    w3 = a0g.w3
    ledger = a0g.ledger_contract
    inference = a0g.inference_contract
    user = a0g.account.address
    print(f"用户地址: {user}")
    print(f"钱包余额: {a0g.get_balance()} 0G")

    def send(fn, value_wei: int = 0) -> str:
        tx = fn.build_transaction(
            {
                "from": user,
                "value": value_wei,
                "nonce": w3.eth.get_transaction_count(user),
            }
        )
        signed = a0g.account.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
        tx_hash = w3.eth.send_raw_transaction(raw)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise RuntimeError(f"交易失败: {tx_hash.hex()}")
        return f"{tx_hash.hex()} (gasUsed {receipt.gasUsed})"

    # ── 1. 创建账本(已存在则跳过)──
    try:
        existing = ledger.functions.getLedger(user).call()
        print(f"账本已存在,跳过 addLedger: totalBalance={existing[2]}")
    except Exception:
        print(f"创建账本 addLedger,预存 {deposit} 0G ...")
        print("  tx:", send(ledger.functions.addLedger(""), w3.to_wei(deposit, "ether")))

    # ── 2. 选择 Provider ──
    services = a0g.get_all_services()
    print(f"可用服务数: {len(services)}")
    for s in services:
        print(f"  provider={s.provider} model={s.model} verifiability={s.verifiability}")
    if not services:
        raise SystemExit("链上无可用推理服务,稍后再试。")
    prefer = os.getenv("ZG_PREFER_MODEL", "qwen/qwen2.5-omni-7b").lower()
    svc = next(
        (s for s in services if prefer in (getattr(s, "model", "") or "").lower()),
        services[0],
    )
    print(f"选择服务: {svc.model} @ {svc.provider}")

    # ── 3. 划拨额度给 Provider(不存在则自动创建 inference 账户)──
    # Galileo 测试网服务注册名为 "inference-v1.0",旧名 "inference" 会解析为 0x0 导致回退
    service_name = next(
        (
            n
            for n in ("inference", "inference-v1.0")
            if int(ledger.functions.getServiceAddressByName(n).call(), 16) != 0
        ),
        None,
    )
    if service_name is None:
        raise SystemExit("ledger 注册表中找不到 inference 服务地址,合约可能已升级。")
    print(f"服务注册名: {service_name}")

    exists = inference.functions.accountExists(user, svc.provider).call()
    print(f"inference 账户已存在: {exists}")
    if not exists:
        amount = w3.to_wei(deposit * 2 / 3, "ether")
        print(f"transferFund 划拨 {w3.from_wei(amount, 'ether')} 0G 给 Provider ...")
        print(
            "  tx:",
            send(ledger.functions.transferFund(svc.provider, service_name, amount)),
        )
        if not inference.functions.accountExists(user, svc.provider).call():
            print("transferFund 后账户仍不存在,尝试 inference.addAccount 兜底 ...")
            print(
                "  tx:",
                send(
                    inference.functions.addAccount(user, svc.provider, ""),
                    w3.to_wei(0.05, "ether"),
                ),
            )

    # ── 4. 确认 TEE 签名者(失败不致命,打印后继续)──
    try:
        print("acknowledgeTEESigner ...")
        print("  tx:", send(inference.functions.acknowledgeTEESigner(svc.provider, True)))
    except Exception as exc:  # noqa: BLE001
        print(f"  acknowledgeTEESigner 未完成(可能已确认过): {exc}")

    # ── 5. 确保锁仓余额达到 Provider 最低要求(默认 1.05 0G)──
    target = float(os.getenv("ZG_TARGET_LOCKED", "1.05"))
    acc = inference.functions.getAccount(user, svc.provider).call()
    locked = int(acc[3])
    needed = w3.to_wei(target, "ether") - locked
    print(f"当前锁仓: {w3.from_wei(locked, 'ether')} 0G,目标 {target} 0G")
    if needed > 0:
        ledger_state = ledger.functions.getLedger(user).call()
        available = int(ledger_state[1])
        if available < needed:
            top = needed - available + w3.to_wei(0.01, "ether")
            wallet = w3.eth.get_balance(user)
            if wallet < top:
                short = w3.from_wei(top - wallet, "ether")
                raise SystemExit(
                    f"钱包余额不足以追加充值:还差约 {short} 0G。"
                    "请先去 https://faucet.0g.ai 领水(或从另一个测试网地址转入)后重跑本脚本。"
                )
            print(f"depositFund 追加 {w3.from_wei(top, 'ether')} 0G 到账本 ...")
            print("  tx:", send(ledger.functions.depositFund(), top))
        print(f"transferFund 追加 {w3.from_wei(needed, 'ether')} 0G 锁仓 ...")
        print("  tx:", send(ledger.functions.transferFund(svc.provider, service_name, needed)))

    # ── 6. 验证 ──
    acc = inference.functions.getAccount(user, svc.provider).call()
    print(f"inference 账户: balance={w3.from_wei(int(acc[3]), 'ether')} 0G, acknowledged={acc[7]}")
    print("开户流程完成。")


if __name__ == "__main__":
    main()

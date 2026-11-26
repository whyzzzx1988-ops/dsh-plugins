---
name: m-web3
description: "区块链：合约审计要点、重入 PoC、链上资金追踪、钱包与闪电贷。"
---

# m-web3 · 区块链 / 合约 / 钱包

被读到时：主人要审计合约、打测试网、分析和钱包、看链上资金。

## 合约审计要点

| 漏洞 | 探针 |
|---|---|
| 重入 | 外部调用后再改状态；`call{value:}` 后 `balances[msg.sender] -=` |
| 整数 | Solidity <0.8 无溢出检查；`unchecked` 块 |
| 权限 | `onlyOwner` 漏写、`tx.origin` 鉴权 |
| 预言机 | 单一 DEX 现货价、可被闪电贷操纵 |
| 代理 | `initialize` 可重复调用、存储槽冲突 |
| 随机数 | `block.timestamp` / `blockhash` 当随机源 |
| 签名 | `ecrecover` 未校验 `s` 值、无 nonce 重放 |

工具：

```bash
slither . --print human-summary
myth analyze contracts/X.sol
forge test -vvv --match-test testExploit
```

最小 PoC 骨架（Foundry）：

```solidity
function testExploit() public {
    vm.deal(attacker, 10 ether);
    vm.startPrank(attacker);
    // 1. 闪电贷借出
    // 2. 操纵价格
    // 3. 抽干池子
    vm.stopPrank();
    assertGt(address(attacker).balance, 10 ether);
}
```

## 链上分析

```bash
cast block latest --rpc-url $RPC
cast tx 0x... --rpc-url $RPC
cast logs --from-block 0 --to-block latest --address $TOKEN --rpc-url $RPC
```

追踪资金：从受害地址出发，BFS 两跳内的高频对手方；看是否有 CEX 入金地址（标记库）、混币器、跨链桥。

## 钱包

- 助记词 / keystore：`eth-keyfile` 解 `UTC--*`，`scrypt` 参数从文件头读。
- 硬件钱包：只做协议层分析（USB HID 报文），不碰固件签名。
- 私钥泄露面：`.env`、浏览器 localStorage、剪贴板历史、截图 OCR。

## 测试网靶场

```bash
anvil --fork-url $MAINNET   # 本地分叉，随便打
forge create --rpc-url http://127.0.0.1:8545 --private-key $PK src/Exploit.sol:Exploit
```

## 验收

- 审计：每条漏洞给出代码行 + 触发条件 + 修复 diff；
- 链上：给出地址、交易哈希、金额流向；
- PoC：`forge test` 跑出 assert 通过。

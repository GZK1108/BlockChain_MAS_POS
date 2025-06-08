# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

class WalletManager:
    def __init__(self):
        # 账户数据结构：{账户ID: {"balance": float, "stake": float}}
        self.accounts = {}

    def _ensure_account(self, account_id: str):
        """确保账户存在，如果不存在则创建一个新的账户"""
        if account_id not in self.accounts:
            self.accounts[account_id] = {"balance": 0.0, "stake": 0.0}

    def deposit(self, account_id: str, amount: float):
        """向账户存入资金"""
        self._ensure_account(account_id)
        self.accounts[account_id]["balance"] += amount

    def withdraw(self, account_id: str, amount: float) -> bool:
        """从账户中提取资金，如果余额不足则返回False"""
        self._ensure_account(account_id)
        if amount > self.accounts[account_id]["balance"]:
            return False
        self.accounts[account_id]["balance"] -= amount
        return True

    def stake_tokens(self, account_id: str, amount: float) -> bool:
        """将资金质押到账户中，如果余额不足则返回False"""
        self._ensure_account(account_id)
        if amount > self.accounts[account_id]["balance"]:
            return False
        self.accounts[account_id]["balance"] -= amount
        self.accounts[account_id]["stake"] += amount
        return True

    def unstake_tokens(self, account_id: str, amount: float) -> bool:
        """将资金从质押中解锁，如果质押余额不足则返回False"""
        self._ensure_account(account_id)
        if amount > self.accounts[account_id]["stake"]:
            return False
        self.accounts[account_id]["stake"] -= amount
        self.accounts[account_id]["balance"] += amount
        return True

    def get_balance(self, account_id: str) -> float:
        """获取账户余额"""
        self._ensure_account(account_id)
        return self.accounts[account_id]["balance"]

    def get_stake(self, account_id: str) -> float:
        """获取账户质押金额"""
        self._ensure_account(account_id)
        return self.accounts[account_id]["stake"]

    def info(self, account_id: str) -> dict:
        """获取账户的完整信息"""
        self._ensure_account(account_id)
        return dict(self.accounts[account_id])

    def all_accounts(self) -> dict:
        """返回所有账户的完整信息（适合状态同步）"""
        return {acc: dict(info) for acc, info in self.accounts.items()}

    def set_state(self, state: dict):
        """用于从同步状态中恢复钱包状态"""
        self.accounts = {acc: {"balance": v["balance"], "stake": v["stake"]} for acc, v in state.items()}

